#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
    Trouve les permissions redondantes dans une arborescence : les utilisateurs qui ont une permission
    définie individuellement alors qu'ils ont déjà cette même permission gràce à leur appartenance à un groupe.

    ATTENTION !
    On compare les permissions EXACTEMENT, on ne montrera pas les permissions inférieures à celles du groupe.
    Exemple un utilisateur qui a un droit de lecture explicite alors qu'il a déjà un contrôle total parce qu'il
    est administrateur.
"""

import argparse
import os
import sys
import fichiers_permissions_liste
import gipkouserinfo

fic_sortie = None


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
def LireParametres():
    if hasattr(sys, 'frozen'):
        Fpgm = sys.executable
    else:
        Fpgm = os.path.realpath(__file__)

    rep = os.path.dirname(Fpgm)
    nom = os.path.splitext(os.path.basename(Fpgm))[0]

    parser = argparse.ArgumentParser(description='Liste des permissions redondantes (user / groupe)')
    parser.add_argument('--output', '-o', action='store', help='Nom du fichier en sortie')
    parser.add_argument('--niveau', '-n', type=int, action='store', help='nombre de niveaux maximal à explorer')
    # parser.add_argument('--fichiers', '-f', action='count', help='Afficher AUSSI les permissions des fichiers')
    parser.add_argument('nomRepBase', default=os.path.realpath('.'), action='store', help='Nom du répertoire à examiner', nargs='?')
    args = parser.parse_args()

    #   On fait quelques vérifications :
    if not os.path.isdir(args.nomRepBase):
        raise NotADirectoryError('%s n\'est pas un répertoire' % args.nomRepBase)

    return args.nomRepBase, args.niveau, args.output


# ------------------------------------------------------------------------------------
def output(ligne):
    global fic_sortie

    if fic_sortie:
        fic_sortie.write(ligne)
    else:
        sys.stdout.write(ligne)


# --------------------------------------------------------------------------------------------------
def trouver_doublons(liste_droits, infos_serveur):
    """
        Cette fonction prend en entrée la liste de droits d'accès sur un fichier ou un répertoire et
        les infos du serveur sur les groupes et les utilisateurs, et compare les droits individuels des
        utilisateurs avec ceux qu'ils ont par leur appartenance à un groupe.

        Elle renvoie une liste de couples utilisateur / groupe où l'utilisateur dispose déjà des mêmes
        droits grâce à son appartenance au groupe.
    """
    liste_doublons = []
    lu = [e for e in liste_droits if e[6] == 'U']  # Les utilisateurs...
    lg = [e for e in liste_droits if e[6] == 'G']  # ...et les groupes

    for ixg in lg:
        users_du_groupe = infos_serveur['groups'][ixg[0]][0]
        for ixu in lu:
            if ixu[0] in users_du_groupe and ixu[1] == ixg[1]:
                liste_doublons.append((ixu, ixg))

    return liste_doublons


# --------------------------------------------------------------------------------------------------
def lister_redondances(rep, niveaumax, nom_fic_sortie, infos_serveur):
    global fic_sortie

    if(nom_fic_sortie):
        fic_sortie = open(nom_fic_sortie, 'w')

    dirs, fics = fichiers_permissions_liste.perm_load(rep, niveaumax, True, False, infos_serveur)
    """
        dirs est une liste d'éléments "droits" pour les répertoires, fics est un dictionnaire dont
        la clé est un nom de répertoire et chaque élément est une liste d'éléments "droits" pour
        les fichiers de ce répertoire.

        Chaque élément "droits" contient :
            élément[0] : nom (du répertoire ou du fichier)
            élément[1] : propriétaire (du répertoire ou du fichier)
            élément[2] : liste des utilisateurs avec pour chacun la liste de ses droits et l'indication User/Group
    """

    nb_trouves = 0
    for d in dirs:
        liste_doublons = trouver_doublons(d[2], infos_serveur)
        ligne_repertoire = '\n%s :\n' % d[0]
        if liste_doublons:
            nb_trouves += len(liste_doublons)
            if ligne_repertoire:
                output(ligne_repertoire)
                ligne_repertoire = ''

            for dbl in liste_doublons:
                output('\t%s a déjà le droit %s parce qu\'il appartient au groupe %s\n' % (dbl[0][0], dbl[0][1], dbl[1][0]))
            output('\n')

        if d[0] in fics:
            for f in fics[d[0]]:
                liste_doublons = trouver_doublons(f[2], infos_serveur)
                if liste_doublons:
                    nb_trouves += len(liste_doublons)
                    if ligne_repertoire:
                        output(ligne_repertoire + '\n')
                        ligne_repertoire = ''

                    for dbl in liste_doublons:
                        output('\tfichier %s : %s a déjà le droit %s parce qu\'il appartient au groupe %s\n' % (f[0], dbl[0][0], dbl[0][1], dbl[1][0]))

    if nb_trouves is 0:
        output('Aucune redondance trouvée\n')

    fic_sortie.close()
    fic_sortie = None


# --------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    rep, niveaumax, nom_fic_sortie = LireParametres()
    adinfo = gipkouserinfo.UserInfo()
    users = adinfo.get_users()
    groups = adinfo.get_groups()
    infos_serveur = {'users': users, 'groups': groups}

    lister_redondances(rep, niveaumax, nom_fic_sortie, infos_serveur)
