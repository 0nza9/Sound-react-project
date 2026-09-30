# Sound React Project

Un visuel de particules qui réagit à la musique, dans TouchDesigner, créé uniquement avec
des scripts Python.

Il n'y a pas de fichier `.toe` dans ce dépôt. À la place, trois scripts construisent tout
le réseau : l'analyse du son, les particules sur GPU, le rendu et les effets. Un quatrième
script fait l'inverse : il relit les réglages faits à la main dans TouchDesigner et les
réécrit dans les scripts. Le visuel et ses réglages restent donc dans du code Python.

## Prérequis

TouchDesigner (testé avec la build 2025.33230). Rien d'autre à installer.

Le projet utilise trois composants de la Palette de TouchDesigner (`audioAnalysis`, `bloom`
et `feedback`). Les scripts vont les chercher tout seuls dans votre installation : vous
n'avez rien à télécharger ni aucun chemin à renseigner.

## Installation

1. Ouvrir un nouveau projet TouchDesigner.
2. Créer un **Base COMP** et le nommer `project1` (les scripts construisent tout dedans).
3. Entrer dedans et créer trois **Text DAT**, nommés `audio_setup`, `pop_setup` et
   `save_settings`. Pour chacun : mettre le chemin du fichier `.py` correspondant dans le
   paramètre **File**, puis cliquer sur **Load on Start**.
4. Ouvrir le Textport (`Alt+T`) et lancer, dans cet ordre :

```python
op('/project1/audio_setup').run()
op('/project1/pop_setup').run()
```

Pour changer de musique : modifier `AUDIO_FILE` en haut de `audio_setup.py`, ou changer
directement le paramètre **File** de `audiofilein1` une fois qu'il existe.

Le résultat s'affiche dans une fenêtre à part, gérée par `window1`.

> **Attention :** tous les opérateurs sont créés au même endroit dans le réseau, les uns
> par-dessus les autres. C'est normal, mais c'est déroutant : on croit facilement qu'un
> opérateur est manquant alors qu'il est simplement caché derrière un autre. Il suffit de
> les déplacer pour y voir clair. Pour vérifier qu'un opérateur existe vraiment, plutôt que
> de le chercher des yeux, taper dans le Textport :
> `print(op('/project1/bloom'))` — si ça affiche `None`, il n'existe pas.

## Les scripts

**`audio_setup.py`** — lit un fichier audio et l'analyse.

Il crée `audiofilein1`, le composant `audioAnalysis`, puis `null1`, qui donne accès aux neuf
valeurs analysées : low, mid, high, kick, snare, rhythm, smsd, fmsd et spectralCentroid.
Il crée aussi `speed1`, qui additionne ces valeurs au fil du temps (voir plus bas), `null2`
pour le signal audio brut, et `audiodevout1` pour entendre le son.

Les réglages d'analyse, à ajuster pour chaque musique, sont dans le dictionnaire
`ANALYSIS_SETTINGS` en haut du fichier.

**`pop_setup.py`** — crée le visuel.

Le signal audio brut est transformé en une ligne de points. Ces points servent de source à
un système de particules qui tourne en boucle sur le GPU. Deux bruits (noise) et une torsion
déforment le nuage, les particules qui s'éloignent trop sont supprimées, puis le tout est
rendu et passé dans les effets.

Les trois liens entre le son et l'image sont des constantes en haut du fichier :

```python
MAP_LOW   = "op('speed1')['mid']*0.5"    # noise2 Translate 4D — déformation large
MAP_FMSD  = "op('speed1')['fmsd']"       # noise1 Translate 4D — déformation fine
MAP_SNARE = "op('null1')['snare']*0.5"   # math1 Multiply — dosage entre les deux bruits
```

On peut mettre n'importe lequel des neuf canaux à la place. La différence entre les deux
sources :

- **`null1`** donne la valeur brute, entre 0 et 1. Elle monte et redescend avec la musique.
- **`speed1`** donne le cumul de cette valeur. Elle ne fait qu'augmenter, ce qui crée un
  mouvement qui avance toujours et ne se répète jamais.

**`save_settings.py`** — sauvegarde vos réglages dans le code.

Une fois que vous avez réglé la musique, les contrôles d'`audioAnalysis` ou les trois
expressions à la main dans TouchDesigner, lancez :

```python
op('/project1/save_settings').run()
```

Le script lit les valeurs actuelles et réécrit `AUDIO_FILE`, `ANALYSIS_SETTINGS` et les
trois constantes `MAP_*` dans les fichiers. La prochaine reconstruction repartira donc
exactement de vos réglages.

## Comment le signal circule

```
audiofilein1 ──┬── audiodevout1                  (pour entendre le son)
               ├── null2 ─────────────────┐      (signal audio brut)
               └── audioAnalysis ── null1 ─┼── speed1
                                           │
  chopto1 ◄────────────────────────────────┘     (le son devient des points)
     └── particle1 ── random1 ── null3 ──┬── feedback1 ──┐
                                         └── merge1 ◄────┘
             merge1 ── mathmix1 ── mathmix2 ── noise2 ──┬── noise1 ──┐
                                                        └── math1 ───┴── mathmix3
             mathmix3 ── twist1 ── delete1 ── endfeedback ──► retour vers feedback1
                                        └── geo1 ── render1
             render1 ── feedback ── bloom ── rgbkey1 ── null4 ── window1
```

`feedback1` et `endfeedback` forment la boucle des particules. Le TOP `feedback`, lui, est
un effet de traînée sur l'image finale. Appuyer sur **1** relance la simulation.

## Remarques

- La couleur et la taille des particules (`pointsprite1`) ne bougent pas. Toute la
  réaction à la musique passe donc par le mouvement et la forme. Faire réagir la couleur
  ou la taille reste à faire.
- Utiliser `speed1` pour le dosage de `mathmix3` pose problème : comme la valeur ne fait
  qu'augmenter, les particules finissent par être projetées trop loin et supprimées.
  `MAP_SNARE` utilise donc `null1`, qui reste entre 0 et 1.
- Pour réagir à du son en direct, il suffit de remplacer `audiofilein1` par un Audio Device
  In CHOP : le reste de la chaîne ne change pas. Un périphérique de bouclage comme VB-Cable
  permet de capter le son de l'ordinateur.
