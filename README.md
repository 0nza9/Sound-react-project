# Sound React Project

Un visuel de particules audio-réactif pour TouchDesigner, construit entièrement à partir de
scripts Python.

Plutôt qu'un fichier `.toe`, ce dépôt contient trois scripts qui construisent tout le réseau —
analyse audio, simulation de particules sur GPU, rendu et post-traitement — dans un projet
vierge. Un quatrième mécanisme relit les réglages faits à la main et les réécrit dans les
scripts : le visuel et son réglage vivent donc dans le dépôt sous forme de Python lisible.

## Prérequis

TouchDesigner (développé avec la build 2025.33230) — rien d'autre.

Le projet utilise trois composants standard de la Palette (`audioAnalysis`, `bloom`,
`feedback`). Les scripts les trouvent directement dans votre installation de TouchDesigner :
rien à télécharger, aucun chemin à configurer.

## Installation

1. Ouvrir un nouveau projet TouchDesigner.
2. Créer un **Base COMP** nommé `project1` (les scripts construisent dans `/project1`).
3. À l'intérieur, créer trois **Text DAT** nommés `audio_setup`, `pop_setup` et
   `save_settings`. Faire pointer le paramètre **File** de chacun vers le fichier `.py`
   correspondant, puis pulser **Load on Start**.
4. Ouvrir le Textport (`Alt+T`) et exécuter, dans cet ordre :

```python
op('/project1/audio_setup').run()
op('/project1/pop_setup').run()
```

Pour changer de morceau, modifier `AUDIO_FILE` en haut de `audio_setup.py`, ou le paramètre
**File** de `audiofilein1` une fois celui-ci créé.

Le résultat s'affiche dans une fenêtre séparée pilotée par `window1`.

## Les scripts

**`audio_setup.py`** — lit un fichier audio et l'analyse. Construit `audiofilein1`, le
composant `audioAnalysis`, `null1` (ses neuf canaux : low, mid, high, kick, snare, rhythm,
smsd, fmsd, spectralCentroid), `speed1` (qui intègre ces canaux en valeurs qui avancent
continûment), `null2` (la forme d'onde stéréo brute) et `audiodevout1`.

Le réglage propre à chaque morceau se trouve dans le dictionnaire `ANALYSIS_SETTINGS`, en
haut du fichier.

**`pop_setup.py`** — construit le visuel. La forme d'onde brute devient une ligne de points,
qui alimente un système de particules tournant dans une boucle de feedback GPU ; deux champs
de bruit et une torsion déforment le nuage, les points trop éloignés sont supprimés, puis le
résultat est rendu et post-traité.

Les trois mappings audio → visuel sont des constantes en haut du fichier :

```python
MAP_LOW   = "op('speed1')['mid']*0.5"    # noise2 Translate 4D — déplacement large
MAP_FMSD  = "op('speed1')['fmsd']"       # noise1 Translate 4D — déplacement fin
MAP_SNARE = "op('null1')['snare']*0.5"   # math1 Multiply — pondération du mélange
```

N'importe lequel des neuf canaux d'analyse peut être substitué. `null1` donne une valeur
brute entre 0 et 1 qui suit la musique instant par instant ; `speed1` en donne l'intégrale,
qui avance toujours et ne se répète donc jamais.

**`save_settings.py`** — l'aller-retour. Après avoir réglé à la main le morceau, les
contrôles d'`audioAnalysis` ou les trois expressions de mapping dans TouchDesigner :

```python
op('/project1/save_settings').run()
```

Le script lit les valeurs en cours et réécrit `AUDIO_FILE`, `ANALYSIS_SETTINGS` et les trois
constantes `MAP_*` sur place, pour que la reconstruction suivante reproduise exactement ce
qui a été réglé.

## Flux du signal

```
audiofilein1 ──┬── audiodevout1                  (écoute)
               ├── null2 ─────────────────┐      (forme d'onde brute)
               └── audioAnalysis ── null1 ─┼── speed1
                                           │
  chopto1 ◄────────────────────────────────┘     (onde → points)
     └── particle1 ── random1 ── null3 ──┬── feedback1 ──┐
                                         └── merge1 ◄────┘
             merge1 ── mathmix1 ── mathmix2 ── noise2 ──┬── noise1 ──┐
                                                        └── math1 ───┴── mathmix3
             mathmix3 ── twist1 ── delete1 ── endfeedback ──► retour vers feedback1
                                        └── geo1 ── render1
             render1 ── feedback ── bloom ── rgbkey1 ── null4 ── window1
```

`feedback1` et `endfeedback` forment la boucle de simulation des particules ; le TOP
`feedback` est une traînée séparée, au niveau de l'image. Appuyer sur **1** relance la
simulation.

## Remarques

- La couleur et la taille de `pointsprite1` sont fixes : la réactivité audio passe donc
  entièrement par le mouvement et la forme. Piloter la couleur ou la taille par l'audio
  reste à explorer.
- Utiliser un canal intégré (`speed1`) comme pondération de mélange le fait croître sans
  limite. `MAP_SNARE` utilise volontairement la valeur brute de `null1` pour rester entre
  0 et 1.
- L'entrée audio en direct fonctionne en remplaçant `audiofilein1` par un Audio Device In
  CHOP, sans rien changer au reste de la chaîne. Un périphérique de bouclage comme VB-Cable
  permet de capter le son du système.
