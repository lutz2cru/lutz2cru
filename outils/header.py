"""Génère l'en-tête SVG du profil (versions claire et sombre).

Le texte est converti en tracés avec la police Geist, comme sur tulz.fr :
GitHub affiche les SVG via <img>, qui ne peut pas charger de police externe.

Usage : python outils/header.py <dossier contenant les .ttf Geist>
Polices attendues : Geist-Regular.ttf, Geist-SemiBold.ttf, GeistMono-Regular.ttf
(disponibles sur Google Fonts, licence OFL).
"""

import sys
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

RACINE = Path(__file__).resolve().parent.parent
LARGEUR, HAUTEUR = 840, 244

# Mêmes valeurs que les variables CSS de tulz.fr
THEMES = {
    "light": {"ink": "#1d1d1f", "ink2": "#4b4b50", "ink3": "#6a6a70", "line": "#d2d2d7", "accent": "#0066cc"},
    "dark": {"ink": "#f5f5f7", "ink2": "#b4b4ba", "ink3": "#8e8e93", "line": "#3d3d42", "accent": "#2997ff"},
}

SURTITRE = "PROFIL GITHUB · LUTZ2CRU"
NOM = "Matthias Lutz"
ROLE = "Apprenti ingénieur Data & IA"
FAITS = [
    ("ARNia BFC", "Apprenti Data & IA depuis sept. 2026"),
    ("UTBM", "Ingénieur informatique, promo 2029"),
    ("tulz.fr", "Parcours, projets et contact"),
]


class Police:
    def __init__(self, chemin):
        self.font = TTFont(chemin)
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.upm = self.font["head"].unitsPerEm

    def largeur(self, texte, taille, interlettre=0.0):
        unites = sum(self.glyphs[self.cmap[ord(c)]].width for c in texte)
        return unites * taille / self.upm + interlettre * taille * (len(texte) - 1)

    def trace(self, texte, x, y, taille, interlettre=0.0):
        """Renvoie le 'd' d'un <path> pour le texte, ligne de base en y."""
        echelle = taille / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        curseur = x
        for c in texte:
            nom = self.cmap.get(ord(c))
            if nom is None:
                raise ValueError(f"Glyphe manquant : {c!r}")
            g = self.glyphs[nom]
            g.draw(TransformPen(pen, (echelle, 0, 0, -echelle, curseur, y)))
            curseur += g.width * echelle + interlettre * taille
        return pen.getCommands()


def couper(police, texte, taille, largeur_max):
    lignes, ligne = [], ""
    for mot in texte.split():
        essai = f"{ligne} {mot}".strip()
        if ligne and police.largeur(essai, taille) > largeur_max:
            lignes.append(ligne)
            ligne = mot
        else:
            ligne = essai
    return lignes + [ligne]


def svg(theme, regular, semibold, mono):
    t = THEMES[theme]
    els = []

    def texte(police, contenu, x, y, taille, couleur, interlettre=0.0):
        d = police.trace(contenu, x, y, taille, interlettre)
        els.append(f'<path fill="{couleur}" d="{d}"/>')

    # Surtitre en mono, précédé d'un carré d'accent
    els.append(f'<rect x="0" y="14" width="8" height="8" fill="{t["accent"]}"/>')
    texte(mono, SURTITRE, 18, 22, 11, t["ink3"], 0.08)

    texte(semibold, NOM, -2, 86, 56, t["ink"], -0.04)
    texte(regular, ROLE, 0, 124, 22, t["ink2"], -0.018)

    # Trois colonnes de faits, séparées par un filet en haut (comme .facts sur le site)
    gouttiere = 32
    col = (LARGEUR - 2 * gouttiere) / 3
    for i, (titre, detail) in enumerate(FAITS):
        x = i * (col + gouttiere)
        els.append(f'<rect x="{x:.1f}" y="168" width="{col:.1f}" height="1" fill="{t["line"]}"/>')
        texte(semibold, titre, x, 202, 20, t["ink"], -0.025)
        for j, ligne in enumerate(couper(regular, detail, 14, col)):
            texte(regular, ligne, x, 228 + j * 20, 14, t["ink3"])

    titre = escape(f"{NOM} — {ROLE}. " + " ".join(f"{a} : {b}." for a, b in FAITS), {'"': "&quot;"})
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{LARGEUR}" height="{HAUTEUR}" '
        f'viewBox="0 0 {LARGEUR} {HAUTEUR}" role="img" aria-label="{titre}">\n'
        f"<title>{titre}</title>\n" + "\n".join(els) + "\n</svg>\n"
    )


def main():
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "fonts")
    regular = Police(dossier / "Geist-Regular.ttf")
    semibold = Police(dossier / "Geist-SemiBold.ttf")
    mono = Police(dossier / "GeistMono-Regular.ttf")
    sortie = RACINE / "assets"
    sortie.mkdir(exist_ok=True)
    for theme in THEMES:
        chemin = sortie / f"header-{theme}.svg"
        chemin.write_text(svg(theme, regular, semibold, mono), encoding="utf-8")
        print(f"{chemin.relative_to(RACINE)} ({chemin.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
