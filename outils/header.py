"""Génère les SVG animés du profil (versions claire et sombre).

- assets/header-{theme}.svg : en-tête (nom, rôle tapé au clavier, trois faits)
- assets/pipeline-{theme}.svg : schéma animé d'une chaîne RAG

Le texte est converti en tracés avec la police Geist, comme sur tulz.fr :
GitHub affiche les SVG via <img>, qui ne peut pas charger de police externe.
Les animations sont en CSS dans le SVG (pas de JavaScript, refusé par GitHub)
et sont coupées si le visiteur a activé « réduire les animations ».

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
LARGEUR = 840
EASE = "cubic-bezier(.16,1,.3,1)"

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

# Chaîne RAG générique (aucun détail interne)
ETAPES = [
    ("Documents", "sources publiques"),
    ("Index", "BM25 + vecteurs"),
    ("Recherche", "hybride, top-k"),
    ("LLM", "génération"),
    ("Réponse", "utilisateur"),
]

REDUIT = "@media (prefers-reduced-motion: reduce){*{animation:none!important}.a,.l{opacity:1;transform:none}.mv{display:none}}"


def nombre(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


class Police:
    def __init__(self, chemin):
        self.font = TTFont(chemin)
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.upm = self.font["head"].unitsPerEm

    def avances(self, texte, taille, interlettre=0.0):
        """Position x de fin de chaque caractère."""
        x, res = 0.0, []
        for c in texte:
            x += self.glyphs[self.cmap[ord(c)]].width * taille / self.upm
            res.append(x)
            x += interlettre * taille
        return res

    def largeur(self, texte, taille, interlettre=0.0):
        return self.avances(texte, taille, interlettre)[-1]

    def trace(self, texte, x, y, taille, interlettre=0.0):
        """Renvoie le 'd' d'un <path> pour le texte, ligne de base en y."""
        echelle = taille / self.upm
        pen = SVGPathPen(self.glyphs, ntos=nombre)
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


def document(largeur, hauteur, titre, style, corps):
    titre = escape(titre, {'"': "&quot;"})
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur}" height="{hauteur}" '
        f'viewBox="0 0 {largeur} {hauteur}" role="img" aria-label="{titre}">\n'
        f"<title>{titre}</title>\n<style>{style}{REDUIT}</style>\n" + "\n".join(corps) + "\n</svg>\n"
    )


def entete(theme, regular, semibold, mono):
    t = THEMES[theme]
    els = []

    def chemin(police, contenu, x, y, taille, couleur, interlettre=0.0, attrs=""):
        d = police.trace(contenu, x, y, taille, interlettre)
        return f'<path fill="{couleur}" d="{d}"{attrs}/>'

    def apparait(contenu, delai):
        els.append(f'<g class="a" style="animation-delay:{delai}s">{contenu}</g>')

    # Surtitre mono et carré d'accent
    apparait(
        f'<rect x="0" y="14" width="8" height="8" fill="{t["accent"]}"/>'
        + chemin(mono, SURTITRE, 18, 22, 11, t["ink3"], 0.08),
        0,
    )
    apparait(chemin(semibold, NOM, -2, 86, 56, t["ink"], -0.04), 0.12)

    # Rôle tapé lettre par lettre : un masque s'élargit au rythme des glyphes,
    # un curseur le suit puis clignote.
    taille_role, inter_role = 22, -0.018
    fins = regular.avances(ROLE, taille_role, inter_role)
    total = fins[-1]
    debut_frappe, duree_frappe = 0.55, 1.4
    n = len(ROLE)
    etapes_clip, etapes_curseur = [], []
    for i in range(n + 1):
        pct = nombre(100 * i / n)
        x = fins[i - 1] if i else 0.0
        etapes_clip.append(f"{pct}%{{transform:scaleX({x / total:.4f})}}")
        etapes_curseur.append(f"{pct}%{{transform:translateX({nombre(x + 2)}px)}}")
    els.append(
        f'<clipPath id="frappe"><rect class="clip" x="0" y="100" width="{nombre(total + 4)}" height="32"/></clipPath>'
        + chemin(regular, ROLE, 0, 124, taille_role, t["ink2"], inter_role, ' clip-path="url(#frappe)"')
        + f'<rect class="caret" x="0" y="105" width="2" height="24" fill="{t["accent"]}"/>'
    )

    # Faits en trois colonnes : le filet se trace, puis le texte apparaît
    gouttiere = 32
    col = (LARGEUR - 2 * gouttiere) / 3
    for i, (titre, detail) in enumerate(FAITS):
        x = i * (col + gouttiere)
        d = 1.7 + 0.15 * i
        els.append(
            f'<rect class="l" style="animation-delay:{d:.2f}s" x="{x:.1f}" y="168" '
            f'width="{col:.1f}" height="1" fill="{t["line"]}"/>'
        )
        bloc = chemin(semibold, titre, x, 202, 20, t["ink"], -0.025)
        for j, ligne in enumerate(couper(regular, detail, 14, col)):
            bloc += chemin(regular, ligne, x, 228 + j * 20, 14, t["ink3"])
        apparait(bloc, round(d + 0.25, 2))

    style = (
        f"@keyframes up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}"
        f".a{{opacity:0;animation:up .9s {EASE} forwards}}"
        f"@keyframes draw{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}"
        f".l{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:draw 1s {EASE} forwards}}"
        f"@keyframes type{{{''.join(etapes_clip)}}}"
        f".clip{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);"
        f"animation:type {duree_frappe}s steps(1,end) {debut_frappe}s forwards}}"
        f"@keyframes suit{{{''.join(etapes_curseur)}}}"
        f"@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}"
        f"@keyframes on{{to{{opacity:1}}}}"
        f".caret{{opacity:0;animation:on 0s {debut_frappe}s forwards,suit {duree_frappe}s steps(1,end) {debut_frappe}s forwards,"
        f"blink 1s step-end {debut_frappe + duree_frappe}s 6 forwards}}"
        "@media (prefers-reduced-motion: reduce){.clip{transform:none}.caret{display:none}}"
    )
    titre = f"{NOM} — {ROLE}. " + " ".join(f"{a} : {b}." for a, b in FAITS)
    return document(LARGEUR, 244, titre, style, els)


def pipeline(theme, regular, semibold, mono):
    t = THEMES[theme]
    hauteur, gap, n = 112, 36, len(ETAPES)
    larg = (LARGEUR - (n - 1) * gap) / n
    y0, h = 16, 72
    duree = 5.0
    els = []

    # Ligne de liaison derrière les boîtes
    els.append(f'<rect x="{nombre(larg / 2)}" y="{y0 + h / 2 - 0.5}" width="{nombre(LARGEUR - larg)}" height="1" fill="{t["line"]}"/>')

    # Point qui circule d'une étape à l'autre, derrière les boîtes :
    # il n'apparaît que dans les intervalles
    debut, fin = larg / 2, LARGEUR - larg / 2
    els.append(f'<circle class="mv dot" cx="{nombre(debut)}" cy="{y0 + h / 2}" r="4" fill="{t["accent"]}"/>')

    images_cle = []
    for i, (titre, detail) in enumerate(ETAPES):
        x = i * (larg + gap)
        cx = x + larg / 2
        p = 100 * i / (n - 1) * 0.8  # le point parcourt 80 % du cycle puis repart
        # Boîte : fond opaque pour masquer la ligne, bordure qui s'allume au passage
        bord = f"b{i}"
        images_cle.append(
            f"@keyframes {bord}{{0%,{nombre(max(p - 4, 0))}%,{nombre(min(p + 10, 100))}%,100%{{stroke:{t['line']}}}"
            f"{nombre(p)}%,{nombre(min(p + 4, 100))}%{{stroke:{t['accent']}}}}}"
            f".{bord}{{animation:{bord} {duree}s linear infinite}}"
        )
        els.append(
            f'<rect class="{bord} bg" x="{nombre(x + 0.5)}" y="{y0 + 0.5}" width="{nombre(larg - 1)}" height="{h - 1}" '
            f'rx="12" stroke="{t["line"]}" stroke-width="1"/>'
        )
        lt = semibold.largeur(titre, 16, -0.02)
        els.append(f'<path fill="{t["ink"]}" d="{semibold.trace(titre, cx - lt / 2, y0 + 33, 16, -0.02)}"/>')
        ld = mono.largeur(detail, 11)
        els.append(f'<path fill="{t["ink3"]}" d="{mono.trace(detail, cx - ld / 2, y0 + 53, 11)}"/>')

    els.append(f'<path fill="{t["ink3"]}" d="{mono.trace("CHAÎNE RAG · SCHÉMA GÉNÉRIQUE", 0, hauteur - 4, 10, 0.08)}"/>')

    # Le fond des boîtes cache la ligne : il prend la couleur de la page GitHub
    fond = "#ffffff" if theme == "light" else "#0d1117"
    style = (
        "".join(images_cle)
        + f".bg{{fill:{fond}}}"
        + f"@keyframes run{{0%{{transform:translateX(0);opacity:0}}3%{{opacity:1}}80%{{transform:translateX({nombre(fin - debut)}px);opacity:1}}"
        + f"86%,100%{{transform:translateX({nombre(fin - debut)}px);opacity:0}}}}"
        + f".dot{{animation:run {duree}s {EASE} infinite}}"
    )
    titre = "Chaîne RAG : " + " → ".join(f"{a} ({b})" for a, b in ETAPES) + "."
    return document(LARGEUR, hauteur, titre, style, els)


def main():
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "fonts")
    regular = Police(dossier / "Geist-Regular.ttf")
    semibold = Police(dossier / "Geist-SemiBold.ttf")
    mono = Police(dossier / "GeistMono-Regular.ttf")
    sortie = RACINE / "assets"
    sortie.mkdir(exist_ok=True)
    for nom, fabrique in (("header", entete), ("pipeline", pipeline)):
        for theme in THEMES:
            chemin = sortie / f"{nom}-{theme}.svg"
            chemin.write_text(fabrique(theme, regular, semibold, mono), encoding="utf-8")
            print(f"{chemin.relative_to(RACINE)} ({chemin.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
