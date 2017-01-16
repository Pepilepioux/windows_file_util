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

    L'argument -a, --all, indique qu'on veut aussi afficher les permissions des groupes système comme
    les administrateurs qui ont par définition un contrôle total partout.

    Historique :

    Version 1.1 2017-01-04
        Si on veut repérer les anomalies il est intéressant d'exclure tous les utilisateurs qu'on
        doit normalement trouver dans toute l'arborescence. Mais dans ce cas on se retrouve avec
        un fichier qui a des tas de lignes qui contiennent juste un nom de répertoire, avec
        aucun utilisateur autorisé. Pour la lisibilité ça fait un peu fouillis...
        S'il n'y a pas de permission à afficher pour un répertoire en tenant compte des exclusions
        on n'affiche donc pas le répertoire.

        De plus on peut avoir des noms de fichiers et de répertoire avec des caractères à la con
        (unicode). Quand on écrit un nom de répertoire ou de fichier il faut donc faire un try/except
        et traiter ces caractères parasites.

    Version 1.2 2017-01-12
        Si on ne donne pas de fichier en sortie on affiche sur le stdout.

        Amélioration de la présentation.

        Par défaut on n'affiche pas les groupes d'administration ni le système qui ont un contrôle total
        partout. Cette liste est définie en dur en début de programme
        Si on veut vraiment les afficher il faut utiliser l'argument -a, --all.

    Version 1.3 2017-01-13
        Déplacement du traitement depuis le main dans une fonction liste_permissions. Ainsi cette fonction peut
        être appelée depuis un autre python. Typiquement pour avoir une liste distincte pour chacun des répertoires
        de premier niveau d'un disque.

"""

import argparse
import os
import sys
import gipkofileinfo

VERSION = '1.3'
fic_sortie = None
LISTE_ADMINS = ['administrateurs de l\'entreprise', 'administrateurs du schéma', 'public folder management', 'domain admins', 'administrateurs', 'système']


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
    parser.add_argument('--output', '-o', action='store', help='Nom de base des fichiers en sortie')
    parser.add_argument('--all', '-a', action='count', help='Affiche aussi les groupes d\'administration (Par défaut ils sont exclus)')
    parser.add_argument('--niveau', '-n', type=int, action='store', help='nombre de niveaux maximal à afficher')
    parser.add_argument('--fichiers', '-f', action='count', help='Afficher AUSSI les permissions des fichiers')
    parser.add_argument('nomRepBase', default=os.path.realpath('.'), action='store', help='Nom du répertoire à examiner', nargs='?')
    args = parser.parse_args()

    #   On fait quelques vérifications :
    if not os.path.isdir(args.nomRepBase):
        raise NotADirectoryError('%s n\'est pas un répertoire' % args.nomRepBase)

    liste_exclusions = [e.strip().lower() for e in args.exclude.split(',') if e != '']

    if args.all is None:
        liste_exclusions += LISTE_ADMINS

    return args.nomRepBase, args.niveau, args.output, liste_exclusions, args.fichiers


# ------------------------------------------------------------------------------------
def output(ligne):
    global fic_sortie

    if fic_sortie:
        fic_sortie[0].write(ligne)
    else:
        sys.stdout.write(ligne)


# ------------------------------------------------------------------------------------
def liste_permissions(nomRepBase, niveaumax, nom_base_sorties, liste_exclusions, fichiers_aussi, progression = False):
    global fic_sortie

    if nomRepBase[-1] != '\\':
        nomRepBase += '\\'

    if niveaumax:
        niveaumax += nomRepBase.count('\\') - 1

    if nom_base_sorties is not None:
        nomFicSortie = [nom_base_sorties + '.txt', nom_base_sorties + '.csv', nom_base_sorties + '.err']
    else:
        nomFicSortie = None

    liste_dirs = [[nomRepBase, gipkofileinfo.get_owner(nomRepBase), gipkofileinfo.get_perm(nomRepBase)]]
    #   Parce que dans le "walk" il n'est pas renvoyé lui-même...
    liste_fics = {}

    lgmax1 = len(nomRepBase)
    #   lgmax1 : longueur du plus long nom de répertoire.
    lgmax2 = 25
    #   lgmax2 : longueur du plus long nom de groupe. Utilisés pour faire une belle présentation
    #   lgmax2 en dur pour pas surcharger la bête en moulinant sur tous les groupes qu'on va rencontrer

    nb = 0
    etapes = '\\|/-'

    """
        Premier passage : on ramène en vrac toutes les infos
    """
    for D, dirs, fics in os.walk(nomRepBase):
        if progression:
            sys.stdout.write('\r\t%s' % etapes[nb % 4])

        if niveaumax:
            niveau = D.count('\\')
            if niveau >= niveaumax:
                continue

        for dir in dirs:
            nomComplet = os.path.join(D, dir)
            niveau = nomComplet.count('\\')

            if progression:
                sys.stdout.write('\r\t%s' % etapes[nb % 4])
                nb += 1

            if len(nomComplet) > lgmax1:
                lgmax1 = len(nomComplet)
                nomlepluslong = nomComplet

            liste_dirs.append([nomComplet, gipkofileinfo.get_owner(nomComplet), gipkofileinfo.get_perm(nomComplet)])

        if fichiers_aussi:
            liste_fics[D] = []
            for fic in fics:
                nomComplet = os.path.join(D, fic)

                if progression:
                    sys.stdout.write('\r\t%s' % etapes[nb % 4])
                    nb += 1

                liste_fics[D].append([fic, gipkofileinfo.get_owner(nomComplet), gipkofileinfo.get_perm(nomComplet)])

    """
        Pour faire plus propre on trie tout ça
    """
    liste_dirs.sort()

    lgmax1 += 5
    chaineformat1 = '\n{0: <%s} {1}\n' % lgmax1  # La ligne "Répertoire"
    chaineformat2 = '        {0: <%s} {1} {2}\n' % lgmax2  # La ligne "Permissions du répertoire"
    chaineformat3 = '\n    {0}\n'  # La ligne "Fichier"
    chaineformat4 = '            {0: <%s} {1: <20} {2}\n' % lgmax2  # La ligne "Permissions du fichier"

    if fic_sortie is None and nomFicSortie:
        fic_sortie = []
        for i in range(len(nomFicSortie)):
            fic_sortie.append(open(nomFicSortie[i], 'w'))

    if fichiers_aussi:
        # Version 1.1 2017-01-04
        # output('\n-------------------------------------')
        ligne_separateur = '\n-------------------------------------'
    else:
        ligne_separateur = ''
        # Fin

    """
        Et c'est parti pour la mise en forme des informations.
    """
    for dir in liste_dirs:
        """
            Version 1.1 2017-01-04
            output(chaineformat1.format(dir[0], dir[1]))

            On n'écrit plus directement la ligne contenant le nom du répertoire, on la prépare
            et on ne l'écrira que si c'est nécessaire, c'est à dire s'il y a une ligne de droits utilisateur
            à écrire

            dir[0] : nom du répertoire
            dir[1] : propriétaire du répertoire
            dir[2] : liste des utilisateurs avec pour chacun la liste de ses droits
        """
        ligne_nom_repertoire = chaineformat1.format(dir[0], dir[1])
        # Fin

        for e in dir[2]:
            if e[0].lower() in liste_exclusions:
                continue

            # Version 1.1 2017-01-04
            if ligne_nom_repertoire:
                if ligne_separateur:
                    output(ligne_separateur)

                try:
                    output(ligne_nom_repertoire)
                except Exception as excpt:
                    texte_remplacement = ''.join([ligne_nom_repertoire[i] if ord(ligne_nom_repertoire[i]) < 255 else '¶' for i in range(len(ligne_nom_repertoire))])
                    output(texte_remplacement)
                    if fic_sortie:
                        fic_sortie[2].write('{1} : Erreur, {0}\n'.format(excpt, texte_remplacement))

                ligne_nom_repertoire = ''
            # Fin Version 1.1 2017-01-04

            output(chaineformat2.format(e[0][:lgmax2], e[1], e[2]))

            if fic_sortie and progression:
                sys.stdout.write('\r\t\t%s' % etapes[nb % 4])
                nb += 1

            try:
                if fic_sortie:
                    fic_sortie[1].write('{0}\t{1}\t\t{2}\t{3}\t{4}\n'.format(dir[0], dir[1], e[0], e[1], e[2]))
            except Exception as excpt:
                texte_remplacement = ''.join([dir[0][i] if ord(dir[0][i]) < 255 else '¶' for i in range(len(dir[0]))])
                if fic_sortie:
                    fic_sortie[1].write('{0}\t{1}\t\t{2}\t{3}\t{4}\n'.format(texte_remplacement, dir[1], e[0], e[1], e[2]))

            if e[0][:6] == 'PySID:':
                try:
                    if fic_sortie:
                        fic_sortie[2].write('Erreur utilisateur {0} dans {1}\n'.format(e[0], dir[0]))
                except Exception as excpt:
                    texte_remplacement = ''.join([dir[0][i] if ord(dir[0][i]) < 255 else '¶' for i in range(len(dir[0]))])
                    if fic_sortie:
                        fic_sortie[2].write('Erreur utilisateur {0} dans {1}\n'.format(e[0], texte_remplacement))

            if dir[1][:6] == 'PySID:':
                try:
                    if fic_sortie:
                        fic_sortie[2].write('Erreur propriétaire {0} dans {1}\n'.format(dir[1], dir[0]))
                except Exception as excpt:
                    texte_remplacement = ''.join([dir[0][i] if ord(dir[0][i]) < 255 else '¶' for i in range(len(dir[0]))])
                    if fic_sortie:
                        fic_sortie[2].write('Erreur propriétaire {0} dans {1}\n'.format(dir[1], texte_remplacement))

        if fichiers_aussi:
            try:
                #   Dans la liste des répertoires certains (au niveau de profondeur maximum spécifié)
                #   n'ont pas été parcourus à la recherche des fichiers. La clé correspondante n'existe
                #   pas. Donc on plante...
                for f in liste_fics[dir[0]]:
                    """
                        Version 1.1 2017-01-04
                        output('\n')
                        output('\t\t{0: <20}\n'.format(f[0]))

                        Idem répertoire plus haut
                    """

                    #   ligne_nom_fichier = '\n\t\t{0: <20}\n'.format(f[0])
                    ligne_nom_fichier = chaineformat3.format(f[0])

                    # Fin Version 1.1 2017-01-04

                    for e in f[2]:
                        if e[0].lower() in liste_exclusions:
                            continue

                        if ligne_nom_repertoire:
                            if ligne_separateur:
                                output(ligne_separateur)

                            try:
                                output(ligne_nom_repertoire)
                            except Exception as excpt:
                                texte_remplacement = ''.join([ligne_nom_repertoire[i] if ord(ligne_nom_repertoire[i]) < 255 else '¶' for i in range(len(ligne_nom_repertoire))])
                                output(texte_remplacement)
                                if fic_sortie:
                                    fic_sortie[2].write('{1} : Erreur, {0}\n'.format(excpt, texte_remplacement))

                            ligne_nom_repertoire = ''

                        if ligne_nom_fichier:
                            try:
                                output(ligne_nom_fichier)
                            except Exception as excpt:
                                texte_remplacement = ''.join([ligne_nom_fichier[i] if ord(ligne_nom_fichier[i]) < 255 else '¶' for i in range(len(ligne_nom_fichier))])
                                output(texte_remplacement)
                                if fic_sortie:
                                    fic_sortie[2].write('{1} : Erreur, {0}\n'.format(excpt, texte_remplacement))

                            ligne_nom_fichier = ''

                        if fic_sortie and progression:
                            sys.stdout.write('\r\t\t%s' % etapes[nb % 4])
                            nb += 1

                        # Là on ne traite que de l'ascii, y'a pas de problème
                        output(chaineformat4.format(e[0][:lgmax2], e[1], e[2]))

                        try:
                            if fic_sortie:
                                fic_sortie[1].write('{0}\t\t{1}\t{2}\t{3}\n'.format(dir[0], f[0], e[0], e[1], e[2]))
                        except Exception as excpt:
                            texte_remplacement_d = ''.join([dir[0][i] if ord(dir[0][i]) < 255 else '¶' for i in range(len(dir[0]))])
                            texte_remplacement_f = ''.join([f[0][i] if ord(f[0][i]) < 255 else '¶' for i in range(len(f[0]))])
                            if fic_sortie:
                                fic_sortie[1].write('{0}\t\t{1}\t{2}\t{3}\n'.format(texte_remplacement_d, texte_remplacement_f, e[0], e[1], e[2]))
                            if fic_sortie:
                                fic_sortie[2].write('{1} , {2} : Erreur, {0}\n'.format(excpt, texte_remplacement_d, texte_remplacement_f))

            except:
                pass

    try:
        for f in fic_sortie:
            f.close()
    except:
        pass

    if fic_sortie:
        print('\n\nListe des permissions de %s inscrite dans %s et %s (erreurs dans %s)' %
              (nomRepBase, nomFicSortie[0], nomFicSortie[1], nomFicSortie[2]))

    fic_sortie = None
    #   Comme il est global il faut le remettre dans son état initial sinon au prochain passage il contiendra
    #   les pointeurs des fichiers précédents, qui sont fermés, et ça plantera.

# ------------------------------------------------------------------------------------
if __name__ == '__main__':
    nomRepBase, niveaumax, nom_base_sorties, liste_exclusions, fichiers_aussi = LireParametres()
    liste_permissions(nomRepBase, niveaumax, nom_base_sorties, liste_exclusions, fichiers_aussi, progression = True)
