#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
    Commande "dir /s" améliorée : affiche à raison d'une ligne par fichier
    - la date du fichier (date de dernière modification)
    - sa taille
    - son nom complet, y compris le chemin

    La sortie se fait soit dans un fichier soit à l'écran. Les champs sont de largeur fixe.
    On peut choisir entre un format destiné à la lecture humaine (date au format ISO, taille arrondie
    exprimée en ko, mo, go) et un format destiné au retraitement.

    On peut faire une sélection sur la taille, la date de dernière modification, l'extension, et une
    expression régulière sur le nom du fichier. ATTENTION cependant avec les expressions régulières :
    toutes les syntaxes possibles n'ont pas été testées, on peut avoir des surprises. Notamment si on
    veut utiliser un chapeau (^) il faut soit le doubler, soit mettre l'expression entre guillemets (")

    Syntaxe :
    ---------
    python gipkodir.py [rep] [--output|-o sortie] [--date-min|-d date mini] [--date-max|-D date maxi]
                       [--size-min|-s taille mini] [--size-max|-S taille maxi] [--extensions|-e extension(s)]
                       [--pattern|-p regexp] [--log-level|-l niveau log] [--human-display|-H]

    rep          : le répertoire, haut de l'arborescence à parcourir. Défaut : répertoire courant.
    sortie       : le nom du fichier dans lequel écrire les résultats. Défaut : affichage à l'écran
    date mini    : on ne traitera que les fichiers postérieurs à cette date.
    date maxi    : on ne traitera que les fichiers antérieurs à cette date.
    taille mini  : on ne traitera que les fichiers dont la taille est supérieure à cette valeur.
                    nombre entier suffixé par une abréviation de taille (k|m|g|t). Ex : "-s 200ko", "-s 1M"
    taille maxi  : on ne traitera que les fichiers dont la taille est inférieure à cette valeur.
    extension(s) : liste d'extensions à prendre en compte, sous la forme ".ext1,.ext2,.extn". Attention,
                    le point fait partie de l'extension ! Tous les fichiers dont l'extension n'est pas
                    dans la liste seront ignorés.
                    Défaut : aucun, on prend toutes les extensions.
    regexp       : une expression régulière que devra matcher le nom du fichier. Attention, c'est une VRAIE
                    expression régulière, pas le "joker" de windows ! Ainsi "n'importe quoi" s'écrira bien
                    ".*" et non simplement "*".
    niveau log   : Quel type d'évènement on inscrira dans le journal. Défaut : warning (30). Le niveau
                    debug (10) liste les fichiers qui ont été éliminé d'après les critères de date, taille,
                    extension ou expression régulière.
                    Le fichier log est gipkodir.log dans le répertoire de l'application.
    -H           : Si spécifié, la date sera affichée au format ISO et les tailles en o, ko, Mo, Go, etc arrondies.
                    Sinon les dates seront affichée au format ISO ET timestamp, les tailles en octets
                    sans séparateur de milliers.

    ATTENTION, il n'y a pas de vérification de cohérence entre les mini et les maxi,
    ni pour les dates, ni pour les tailles !

    Historique :
    ------------

    Version 1.0 2018-04-04
        Original.

"""

import argparse
import os
import sys
import logging
import logging.handlers
import traceback
import datetime
import re
from gipkofileinfo import *

fic_sortie = None


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
def LireParametres():
    if hasattr(sys, 'frozen'):
        Fpgm = sys.executable
    else:
        Fpgm = os.path.realpath(__file__)

    rep = os.path.dirname(Fpgm)
    nom = os.path.splitext(os.path.basename(Fpgm))[0]
    nomFichierLog = os.path.join(rep, nom) + '.log'

    patSize = '^\d{1,3}[kmgt]?o?$'

    parser = argparse.ArgumentParser(description='Dir amélioré')
    parser.add_argument('--output', '-o', action='store', help='Nom du fichier qui contiendra le résultat. Si absent, affichage à l\'écran.')
    parser.add_argument('--date-min', '-d', action='store', help='Ne prendre en compte que les fichiers postérieurs à cette date (format ISO)')
    parser.add_argument('--date-max', '-D', action='store', help='Ne prendre en compte que les fichiers antérieurs à cette date (format ISO)')
    parser.add_argument('--size-min', '-s', action='store', help='Ne prendre en compte que les fichiers de taille supérieure à cette valeur. Format : nnnko/mo/go')
    parser.add_argument('--size-max', '-S', action='store', help='Ne prendre en compte que les fichiers de taille inférieure à cette valeur. Format : nnnko/mo/go')
    parser.add_argument('--extensions', '-e', action='store', help='Extension(s) prise(s) en compte. format ".xt1,.xt2,.xtn"')
    parser.add_argument('--pattern', '-p', action='store', help='Expression régulière de sélection')
    parser.add_argument('--log-level', '-l', default='30', action='store', help='Niveau de log')
    parser.add_argument('--human-display', '-H', action='count', help='Affichage lisible pour un humain')
    parser.add_argument('nomRepBase', default=os.path.realpath('.'), action='store', help='Nom du répertoire à examiner', nargs='?')
    args = parser.parse_args()

    #   On fait quelques vérifications :
    if not os.path.isdir(args.nomRepBase):
        raise NotADirectoryError('%s n\'est pas un répertoire' % args.nomRepBase) from None

    if args.date_min:
        try:
            dateMin = datetime.datetime.strptime(args.date_min, '%Y-%m-%d').timestamp()
        except:
            raise ValueError('Date min incorrecte, %s' % args.date_min) from None
    else:
        dateMin = None

    if args.date_max:
        try:
            dateMax = datetime.datetime.strptime(args.date_max, '%Y-%m-%d').timestamp()
        except:
            raise ValueError('Date max incorrecte, %s' % args.date_max) from None
    else:
        dateMax = None

    if args.size_min:
        if not re.search(patSize, args.size_min, re.I):
            raise ValueError('Taille min incorrecte, %s' % args.size_min) from None
        else:
            facteur = 1000000000000 if re.search('t', args.size_min, re.I) \
                else (1000000000 if re.search('g', args.size_min, re.I)
                      else (1000000 if re.search('m', args.size_min, re.I)
                            else (1000 if re.search('k', args.size_min, re.I)
                                  else 1)))
            sizeMin = int(re.search('^\d+', args.size_min).group()) * facteur
    else:
        sizeMin = None

    if args.size_max:
        if not re.search(patSize, args.size_max, re.I):
            raise ValueError('Taille max incorrecte, %s' % args.size_max) from None
        else:
            facteur = 1000000000000 if re.search('t', args.size_max, re.I) \
                else (1000000000 if re.search('g', args.size_max, re.I)
                      else (1000000 if re.search('m', args.size_max, re.I)
                            else (1000 if re.search('k', args.size_max, re.I)
                                  else 1)))
            sizeMax = int(re.search('^\d+', args.size_max).group()) * facteur
    else:
        sizeMax = None

    if args.extensions:
        extensions = args.extensions.split(',')
    else:
        extensions = None

    if args.pattern:
        try:
            pattern = re.compile(args.pattern, re.I)
        except:
            raise ValueError('%s n\'est pas une expression régulière correcte' % pattern) from None

    else:
        pattern = None

    if args.output:
        ficSortie = args.output
    else:
        ficSortie = None

    try:
        niveauLog = int(args.log_level)
    except:
        niveauLog = logging.WARNING

    humainementLisible = True if args.human_display else False

    return args.nomRepBase, dateMin, dateMax, sizeMin, sizeMax, extensions, pattern, ficSortie, nomFichierLog, niveauLog, humainementLisible


# ------------------------------------------------------------------------------------
def output(ligne):
    #   global fic_sortie
    ligne += '\n'

    if fic_sortie:
        fic_sortie.write(ligne)
    else:
        sys.stdout.write(ligne)


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
def creer_logger(nomFichierLog, niveauLog):
    logger = logging.getLogger()
    logger.setLevel(niveauLog)
    formatter = logging.Formatter('%(asctime)s	%(levelname)s	%(message)s')
    Handler = logging.handlers.WatchedFileHandler(nomFichierLog)
    Handler.setLevel(niveauLog)
    Handler.setFormatter(formatter)
    Handler.set_name('Normal')
    logger.addHandler(Handler)


# ------------------------------------------------------------------------------------
if __name__ == '__main__':
    nomRepBase, dateMin, dateMax, sizeMin, sizeMax, extensions, pattern, ficSortie, nomFichierLog, niveauLog, humainementLisible = LireParametres()
    logger = logging.getLogger()
    creer_logger(nomFichierLog, niveauLog)
    logger.info('Début programme')

    if ficSortie:
        try:
            fic_sortie = open(ficSortie, 'w')
        except:
            raise IOError('Impossible d\'ouvrir le fichier %s en écriture' % ficSortie) from None

    liste = []

    for D, dirs, fics in os.walk(nomRepBase):
        for fic in fics:
            nomComplet = os.path.join(D, fic)

            #   Premier test tout simple : le filtre sur les extensions
            if extensions and os.path.splitext(os.path.basename(nomComplet))[1] not in extensions:
                logger.debug('%s éliminé à cause de son extension' % nomComplet)
                continue

            #   Deuxième test, simple aussi : le filtre sur la pattern
            if pattern and not re.search(pattern, fic):
                logger.debug('%s éliminé par l\'expression régulière' % nomComplet)
                continue

            #   Maintenant on a besoin de la taille et des dates des fichiers.
            try:
                #   Oui, on n'est pas à l'abri d'un nom trop long qui va nous planter...
                taille = os.path.getsize(nomComplet)
            except:
                logger.error('Impossible d\'avoir la taille du fichier %s' % nomComplet)
                continue

            try:
                dateCre = os.path.getctime(nomComplet)
            except:
                logger.error('Impossible d\'avoir la date de création du fichier %s' % nomComplet)
                continue

            try:
                dateMod = os.path.getmtime(nomComplet)
            except:
                logger.error('Impossible d\'avoir la date de modification du fichier %s' % nomComplet)
                continue

            """
                Le gag des dates avec windows :
                Si on crée un fichier f1 le 1 janvier, qu'on le modifie le 15 janvier, et que le 1 février on
                copie ce fichier f1 en fichier f2, le fichier f1 aura bien comme date de création le 1 janvier
                et comme date de modification le 15 janvier, mais le fichier f2 aura, lui, comme date de
                modification le 15 janvier et comme date de création le 1 janvier !
                Microsoft nous a inventé la machine à remonter le temps...

                On va donc se baser sur la date de modification
            """

            if dateMin and dateMod < dateMin:
                logger.debug('%s éliminé parce qu\'antérieur à date min' % nomComplet)
                continue

            if dateMax and dateMod > dateMax:
                logger.debug('%s élimaxé parce que postérieur à date max' % nomComplet)
                continue

            if sizeMin and taille < sizeMin:
                logger.debug('%s éliminé parce que plus petit que taille min' % nomComplet)
                continue

            if sizeMax and taille > sizeMax:
                logger.debug('%s éliminé parce que plus grand que taille max' % nomComplet)
                continue

            liste.append([dateMod, taille, nomComplet])

    for e in liste:
        if humainementLisible:
            ligne = dateISO(e[0]) + '   {: >10s}'.format(affichageHumain(e[1])) + '   ' + e[2]
        else:
            ligne = '{: >15.3f}'.format(e[0]) + ' ' + dateISO(e[0]) + ' ' + '{: >12d}'.format(e[1]) + ' ' + e[2]
        output(ligne)

    if fic_sortie:
        fic_sortie.close()
