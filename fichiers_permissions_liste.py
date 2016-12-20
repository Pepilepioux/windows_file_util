#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
    Liste des permissions sur les répertoires

    Ce programme parcourt récursivement le répertoire passé en argument, et pour
    chaque sous-répertoire il donne la liste des utilisateurs (ou groupes) qui
    disposent d'une permission (ou d'un refus) sur ce répertoire, avec le type de
    permission.

    Ces permissions sont inscrites dans deux fichiers, l'un au format texte lisible
    par un humain, l'autre au format csv (séparateur tab) utilisable pour
    retraitement dans un tableur.

    L'argument -n, --niveau, indique le nombre de niveaux maximal à afficher.
    Par défaut on parcourt toute l'arborescence.

    L'argument -o, --output, donne le nom de base des fichiers résultat. Les
    extensions .txt et .csv sont ajoutées par le programme.

    L'argument -e, --exclude, donne la liste des groupes et utilisateurs à exclure
    de l'affichage pour ne pas le surcharger. Typiquement les administrateurs,
    les opérateurs de sauvegarde qui ont systématiquement tous les droits.
    C'est une liste de valeurs séparées par des virgules, à mettre entre
    guillemets si un nom contient des espaces.
    Typiquement on mettra -e "Administrateurs , Système, Domain Admins, Administrateurs de l'entreprise"

    L'argument -f, --fichiers, indique qu'on veut aussi afficher les permissions des fichiers.
    Par défaut on ne traite que les répertoires.

"""

import argparse
import os
import sys
import gipkofileinfo


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
def LireParametres():
    if hasattr(sys, 'frozen'):
        Fpgm = sys.executable
    else:
        Fpgm = os.path.realpath(__file__)

    rep = os.path.dirname(Fpgm)
    nom = os.path.splitext(os.path.basename(Fpgm))[0]

    parser = argparse.ArgumentParser(description='Liste des permissions sur les répertoires')
    parser.add_argument('--exclude', '-e', action='store', help='Utilisateurs à exclure de l\'affichage', default='')
    parser.add_argument('--output', '-o', action='store', help='Nom de base des fichiers en sortie', default=os.path.join(rep, nom))
    parser.add_argument('--niveau', '-n', type=int, action='store', help='nombre de niveaux maximal à afficher')
    parser.add_argument('--fichiers', '-f', action='count', help='Afficher AUSSI les permissions des fichiers')
    parser.add_argument('nomRepBase', default=os.path.realpath('.'), action='store', help='Nom du répertoire à examiner', nargs='?')
    args = parser.parse_args()

    #   On fait quelques vérifications :
    if not os.path.isdir(args.nomRepBase):
        raise NotADirectoryError('%s n\'est pas un répertoire' % args.nomRepBase)

    liste_exclusions = [e.strip().lower() for e in args.exclude.split(',') if e != '']

    return args.nomRepBase, args.niveau, args.output, liste_exclusions, args.fichiers


# ------------------------------------------------------------------------------------


nomRepBase, niveaumax, nomFicSortie, liste_exclusions, fichiers_aussi = LireParametres()

if nomRepBase[-1] != '\\':
    nomRepBase += '\\'

if niveaumax:
    niveaumax += nomRepBase.count('\\') - 1

nomFicSortie1 = nomFicSortie + '.txt'
nomFicSortie2 = nomFicSortie + '.csv'
nomFicSortie3 = nomFicSortie + '.err'
liste_dirs = []
liste_fics = {}


lgmax = 0
nb = 0

for D, dirs, fics in os.walk(nomRepBase):
    if niveaumax:
        niveau = D.count('\\')
        if niveau >= niveaumax:
            continue

    for dir in dirs:
        nomComplet = os.path.join(D, dir)
        niveau = nomComplet.count('\\')

        nb += 1
        if nb % 100 == 0:
            print(nb, nomComplet)

        if len(nomComplet) > lgmax:
            lgmax = len(nomComplet)
            nomlepluslong = nomComplet

        liste_dirs.append([nomComplet, gipkofileinfo.get_owner(nomComplet), gipkofileinfo.get_perm(nomComplet)])

    if fichiers_aussi:
        liste_fics[D] = []
        for fic in fics:
            nomComplet = os.path.join(D, fic)
            liste_fics[D].append([fic, gipkofileinfo.get_owner(nomComplet), gipkofileinfo.get_perm(nomComplet)])


liste_dirs.sort()

lgmax += 5
chaineformat = '\n{0: <%s} {1}\n' % lgmax

ficSortie1 = open(nomFicSortie1, 'w')
ficSortie2 = open(nomFicSortie2, 'w')
ficSortie3 = open(nomFicSortie3, 'w')

for dir in liste_dirs:
    if fichiers_aussi:
        ficSortie1.write('\n-------------------------------------')

    ficSortie1.write(chaineformat.format(dir[0], dir[1]))
    for e in dir[2]:
        if e[0].lower() in liste_exclusions:
            continue

        ficSortie1.write('\t{0: <20} {1} {2}\n'.format(e[0], e[1], e[2]))
        ficSortie2.write('{0}\t{1}\t\t{2}\t{3}\t{4}\n'.format(dir[0], dir[1], e[0], e[1], e[2]))

        if e[0][:6] == 'PySID:':
            ficSortie3.write('Erreur utilisateur {0} dans {1}\n'.format(e[0], dir[0]))

        if dir[1][:6] == 'PySID:':
            ficSortie3.write('Erreur propriétaire {0} dans {1}\n'.format(dir[1], dir[0]))

    if fichiers_aussi:
        try:
            #   Dans la liste des répertoires certains (au niveau de profondeur maximum spécifié)
            #   n'ont pas été parcourus à la recherche des fichiers. La clé correspondante n'existe
            #   pas. Donc on plante...
            for f in liste_fics[dir[0]]:
                ficSortie1.write('\n')
                ficSortie1.write('\t\t{0: <20}\n'.format(f[0]))

                for e in f[2]:
                    ficSortie1.write('\t\t\t{0: <20} {1} {2}\n'.format(e[0], e[1], e[2]))
                    ficSortie2.write('{0}\t\t{1}\t{2}\t{3}\n'.format(dir[0], f[0], e[0], e[1], e[2]))

        except:
            pass

ficSortie1.close()
ficSortie2.close()
ficSortie3.close()

print('Liste des permissions de %s inscrite dans %s et %s (erreurs dans %s)' %
      (nomRepBase, nomFicSortie1, nomFicSortie2, nomFicSortie3))

exit()
