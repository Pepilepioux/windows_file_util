﻿#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import os
import sys
import gipkofileinfo
import win32security


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
def LireParametres():
    if hasattr(sys, 'frozen'):
        Fpgm = sys.executable
    else:
        Fpgm = os.path.realpath(__file__)

    rep = os.path.dirname(Fpgm)
    nom = os.path.splitext(os.path.basename(Fpgm))[0]

    parser = argparse.ArgumentParser(description='Suppression des permissions sur les fichiers et répertoires')

    help_text = 'Utilisateurs dont il faut supprimer les droits.\nListe de noms séparés par des virgules, entre guillements s\'il y a des espaces'
    parser.add_argument('--users', '-u', action='store', help=help_text)
    parser.add_argument('--verbose', '-v', action='count', help='Affichier le détail des opérations')
    help_text = 'Nom du répertoire de base à traiter. Par défaut, le répertoire courant'
    parser.add_argument('nomRepBase', default=os.path.realpath('.'), action='store', help=help_text, nargs='?')
    args = parser.parse_args()

    #   On fait quelques vérifications :
    if not os.path.isdir(args.nomRepBase):
        raise NotADirectoryError('%s n\'est pas un répertoire' % args.nomRepBase)

    if args.users:
        liste_users = [e.strip().lower() for e in args.users.split(',') if e != '']
    else:
        raise ValueError('L\'utilisateur à traiter (ou une liste d\'utilisateurs) est obligatoire')

    verbose = args.verbose if args.verbose else 0

    return args.nomRepBase, verbose, liste_users


#   -----------------------------------------------------------------------

nomRepBase, verbose, liste_users = LireParametres()

for D, dirs, fics in os.walk(nomRepBase):
    for dir in dirs:
        nomComplet = os.path.join(D, dir)
        if verbose >= 2:
            try:
                #   "Try" parce qu'avec les zozos qui s'obstinnent à mettre des symboles euro
                #   dans leurs noms de fichiers ça plante...
                print('\tOn traite %s' % nomComplet)
            except:
                pass
        gipkofileinfo.remove_perm(nomComplet, *liste_users, verbose=verbose)

    for fic in fics:
        nomComplet = os.path.join(D, fic)
        if verbose >= 2:
            try:
                #   "Try" parce qu'avec les zozos qui s'obstinnent à mettre des symboles euro
                #   dans leurs noms de fichiers ça plante...
                print('\tOn traite %s' % nomComplet)
            except:
                pass
        gipkofileinfo.remove_perm(nomComplet, *liste_users, verbose=verbose)