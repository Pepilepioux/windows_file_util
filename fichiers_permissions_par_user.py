#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
    Liste des permissions par utilisateur

    Ce programme parcourt récursivement le répertoire passé en argument, et pour
    chaque fichier il indique si l'utilisateur passé en argument a un accès en lecture
    ou en écriture.

    L'argument -o, --output, donne le nom du fichier résultat.

"""

import argparse
import os
import sys
import gipkofileinfo
import gipkouserinfo

VERSION = '1.0'
fic_sortie = None
PERMISSIONS = {1: 'Lecture', 2: '        Écriture'}
#   Des espaces pour un meilleur contraste visuel.


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
def LireParametres():
    if hasattr(sys, 'frozen'):
        Fpgm = sys.executable
    else:
        Fpgm = os.path.realpath(__file__)

    rep = os.path.dirname(Fpgm)
    nom = os.path.splitext(os.path.basename(Fpgm))[0]

    parser = argparse.ArgumentParser(description='Liste des permissions par utilisateur')
    parser.add_argument('--output', '-o', action='store', help='Nom de base des fichiers en sortie')
    parser.add_argument('--user', '-u', action='store', help='Utilisateur à tester')
    parser.add_argument('--serveur', '-s', action='store', help='Serveur d\'authentification', default=os.environ.get('LOGONSERVER'))
    parser.add_argument('nomRepBase', default=os.path.realpath('.'), action='store', help='Nom du répertoire à examiner', nargs='?')
    args = parser.parse_args()

    #   On fait quelques vérifications :
    if not os.path.isdir(args.nomRepBase):
        raise NotADirectoryError('%s n\'est pas un répertoire' % args.nomRepBase)

    if args.user is None:
        raise ValueError('L\'argument "utilisateur (-u, --user) est obligatoire')

    return args.nomRepBase, args.user, args.output, args.serveur


# ------------------------------------------------------------------------------------
def output(ligne):
    if fic_sortie:
        fic_sortie.write(ligne)
    else:
        sys.stdout.write(ligne)


# ------------------------------------------------------------------------------------

nomRepBase, user, nomFicSortie, serveur = LireParametres()
user_info = gipkouserinfo.UserInfo(serveur)

if nomRepBase[-1] != '\\':
    nomRepBase += '\\'

liste_dirs = [[nomRepBase, gipkofileinfo.get_user_s_perm(nomRepBase, user, user_info)[0]]]
liste_fics = {}

lgmax = len(nomRepBase)
nb = 0
etapes = '\\|/-'

"""
    Premier passage : on ramène en vrac toutes les infos
"""
for D, dirs, fics in os.walk(nomRepBase):
    # sys.stdout.write('\r\t%s' % etapes[nb % 4])
    # print('----------------\nOn traite %s' % D)

    for dir in dirs:
        nomComplet = os.path.join(D, dir)
        niveau = nomComplet.count('\\')

        # sys.stdout.write('\r\t%s' % etapes[nb % 4])
        nb += 1

        if len(nomComplet) > lgmax:
            lgmax = len(nomComplet)
            nomlepluslong = nomComplet

        permission = gipkofileinfo.get_user_s_perm(nomComplet, user, user_info)
        # print('\tpermission répertoire (%s, %s) = %s' % ( nomComplet, user, permission))
        if permission[0] > 0:
            liste_dirs.append([nomComplet, permission[0]])

    liste_fics[D] = []
    for fic in fics:
        nomComplet = os.path.join(D, fic)

        # sys.stdout.write('\r\t%s' % etapes[nb % 4])
        nb += 1

        permission = gipkofileinfo.get_user_s_perm(nomComplet, user, user_info)
        # print('\tpermission fichier (%s, %s) = %s' % ( nomComplet, user, permission))
        if permission[0] > 0:
            liste_fics[D].append([fic, permission[0]])

"""
    Pour faire plus propre on trie tout ça
"""
liste_dirs.sort()

lgmax += 5
chaineformatdir = '\n{0: <%s} {1}\n' % lgmax
chaineformatfic = '    {0: <%s} {1}\n' % (lgmax - 4)

if nomFicSortie:
    fic_sortie = open(nomFicSortie, 'w')

output('\tPermissions de l\'utilisateur %s sur l\'arborescence de %s :\n' % (user, nomRepBase))
for dir in liste_dirs:
    if dir[1] in PERMISSIONS:
        ligne_nom_repertoire = chaineformatdir.format(dir[0], PERMISSIONS[dir[1]])
        output(ligne_nom_repertoire)

    for f in liste_fics[dir[0]]:
        ligne_nom_fichier = chaineformatfic.format(f[0], PERMISSIONS[f[1]])
        output(ligne_nom_fichier)

if fic_sortie:
    print('\n\nListe des permissions de %s sur %s inscrite dans %s' % (user, nomRepBase, nomFicSortie))

try:
    ficSortie.close()
except:
    pass

exit()
