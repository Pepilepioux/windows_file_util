#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
    Générateur renvoyant les infos sur les fichiers d'une arborescence qui remplissent
    les conditions données.

    Renvoie un tuple répertoire contenant le fichier, nom du fichier, taille,
    date de modification.

    On peut faire une sélection sur la taille, la date de dernière modification,
    l'extension, une expression régulière sur le nom du fichier, ou une
    expression régulière sur le contenu du fichier (pertinent uniquement pour
    les fichiers texte).
    ATTENTION cependant avec les expressions régulières : toutes les syntaxes
    possibles n'ont pas été testées, on peut avoir des surprises. Notamment si
    on veut utiliser un chapeau (^) il faut soit le doubler, soit mettre
    l'expression entre guillemets (")

    Arguments :
    ---------
    1° argument, positionnel, obligatoire : le nom du répertoire à explorer.

    autres arguments, nommés, facultatifs :

    date_min        : format ISO, AAAA-MM-JJ ou AAAA-MM-JJTHH:mm:ss,
                        seuls les fichiers modifiés après cette date sont sélectionnés.

    date_max        : format ISO, AAAA-MM-JJ ou AAAA-MM-JJTHH:mm:ss,
                        seuls les fichiers modifiés avant cette date sont sélectionnés.

    size_min        : nombre entier suffixé par une abréviation de taille (k|m|g|t)?o?.
                        Ex : size_min='200ko', size-min='1M'.
                        Seuls les fichiers dont la taille est supérieure à cette valeur
                        sont sélectionnés.

    size_max        : idem, Seuls les fichiers dont la taille est inférieure à cette valeur
                        sont sélectionnés.

    extensions      : liste d'extensions à prendre en compte, sous la forme
                       ".ext1,.ext2,.extn".
                       Attention, le point fait partie de l'extension ! Seuls les
                       fichiers dont l'extension est dans la liste seront sélectionnés.
                       Défaut : aucun, on prend toutes les extensions.

    pattern         : une expression régulière que devra matcher le nom COMPLET du
                       fichier (y compris l'arborescence de répertoires). Attention,
                       c'est une VRAIE expression régulière, pas le "joker" de
                       windows !
                       Ainsi "n'importe quoi" s'écrira bien ".*" et non
                       simplement "*". Pour spécifier une expression que devront
                       matcher les répertoires mettre évidemmet \\\\ autour dans la
                       regexp...

    texte_cherche   : une expression régulière que devra matcher le contenu du
                       fichier. Attention, comme c'est toujours traité comme une
                       expression régulière il faut penser à échapper les caractères
                       spéciaux comme le point, l'étoile, l'antislash etc.
                       Si cet argument est spécifié et qu'un fichier ne peut pas
                       être lu (pas du texte, problème d'encodage etc) ce fichier
                       ne sera pas selectionné.

    def_encoding    : encodage des fichiers cherchés.
                        Si l'argument texte_cherche est spécifié ça peut être utile.
                        Un fichier encodé en utf-8 sera lu sans problème, mais on
                        n'aura pas de match sur les patterns contenant des caractères
                        accentués...

    ---------------------------------------------------------------------------
    Historique :
    ------------

    Version 1.0 2021-06-13
        Original.

"""

import os
import logging
import datetime
import re


# ------------------------------------------------------------------------------------
def gipkowalk(nom_rep_base, **kwargs):
    logger = logging.getLogger()
    pat_size = '^\d{1,3}[kmgt]?o?$'

    if 'date_min' in kwargs:
        try:
            date_min = datetime.datetime.strptime(kwargs['date_min'], '%Y-%m-%dT%H:%M:%S').timestamp()
        except:
            try:
                date_min = datetime.datetime.strptime(kwargs['date_min'], '%Y-%m-%d %H:%M:%S').timestamp()
            except:
                try:
                    date_min = datetime.datetime.strptime(kwargs['date_min'], '%Y-%m-%d').timestamp()
                except:
                    raise ValueError('Date min incorrecte, %s' % kwargs['date_min']) from None
    else:
        date_min = None

    if 'date_max' in kwargs:
        try:
            date_max = datetime.datetime.strptime(kwargs['date_max'], '%Y-%m-%dT%H:%M:%S').timestamp()
        except:
            try:
                date_max = datetime.datetime.strptime(kwargs['date_max'], '%Y-%m-%d %H:%M:%S').timestamp()
            except:
                try:
                    date_max = datetime.datetime.strptime(kwargs['date_max'], '%Y-%m-%d').timestamp()
                except:
                    raise ValueError('Date max incorrecte, %s' % kwargs['date_max']) from None
    else:
        date_max = None

    if 'size_min' in kwargs:
        if not re.search(pat_size, kwargs['size_min'], re.I):
            raise ValueError('Taille min incorrecte, %s' % kwargs['size_min']) from None
        else:
            facteur = 1000000000000 if re.search('t', kwargs['size_min'], re.I) \
                else (1000000000 if re.search('g', kwargs['size_min'], re.I)
                      else (1000000 if re.search('m', kwargs['size_min'], re.I)
                            else (1000 if re.search('k', kwargs['size_min'], re.I)
                                  else 1)))
            size_min = int(re.search('^\d+', kwargs['size_min']).group()) * facteur
    else:
        size_min = None

    if 'size_max' in kwargs:
        if not re.search(pat_size, kwargs['size_max'], re.I):
            raise ValueError('Taille max incorrecte, %s' % kwargs['size_max']) from None
        else:
            facteur = 1000000000000 if re.search('t', kwargs['size_max'], re.I) \
                else (1000000000 if re.search('g', kwargs['size_max'], re.I)
                      else (1000000 if re.search('m', kwargs['size_max'], re.I)
                            else (1000 if re.search('k', kwargs['size_max'], re.I)
                                  else 1)))
            size_max = int(re.search('^\d+', kwargs['size_max']).group()) * facteur
    else:
        size_max = None

    if 'extensions' in kwargs:
        extensions = kwargs['extensions'].split(',')
    else:
        extensions = None

    if 'pattern' in kwargs:
        try:
            pattern = re.compile(kwargs['pattern'], re.I)
        except:
            raise ValueError('%s n\'est pas une expression régulière correcte' % pattern) from None

    else:
        pattern = None

    if 'texte_cherche' in kwargs:
        try:
            texte_cherche = re.compile(kwargs['texte_cherche'], re.I)
        except:
            raise ValueError('%s n\'est pas une expression régulière correcte' % texte_cherche) from None
    else:
        texte_cherche = None

    if 'def_encoding' in kwargs:
        def_encoding = kwargs['def_encoding']
    else:
        def_encoding = None

    for D, dirs, fics in os.walk(nom_rep_base):
        for fic in fics:
            nom_complet = os.path.join(D, fic)

            #   Premier test tout simple : le filtre sur les extensions
            if extensions and os.path.splitext(os.path.basename(nom_complet))[1] not in extensions:
                logger.debug('%s éliminé à cause de son extension' % nom_complet)
                continue

            #   Deuxième test, simple aussi : le filtre sur la pattern
            #   if pattern and not re.search(pattern, fic):
            if pattern and not re.search(pattern, nom_complet):
                logger.debug('%s éliminé par l\'expression régulière sur le nom' % nom_complet)
                continue

            #   Maintenant on a besoin de la taille et des dates des fichiers.
            try:
                #   Oui, on n'est pas à l'abri d'un nom trop long qui va nous planter...
                taille = os.path.getsize(nom_complet)
            except:
                logger.error('Impossible d\'avoir la taille du fichier %s' % nom_complet)
                continue

            try:
                date_cre = os.path.getctime(nom_complet)
            except:
                logger.error('Impossible d\'avoir la date de création du fichier %s' % nom_complet)
                continue

            try:
                date_mod = os.path.getmtime(nom_complet)
            except:
                logger.error('Impossible d\'avoir la date de modification du fichier %s' % nom_complet)
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

            if date_min and date_mod < date_min:
                logger.debug('%s éliminé parce qu\'antérieur à date min' % nom_complet)
                continue

            if date_max and date_mod > date_max:
                logger.debug('%s éliminé parce que postérieur à date max' % nom_complet)
                continue

            if size_min and taille < size_min:
                logger.debug('%s éliminé parce que plus petit que taille min' % nom_complet)
                continue

            if size_max and taille > size_max:
                logger.debug('%s éliminé parce que plus grand que taille max' % nom_complet)
                continue

            if texte_cherche:
                try:
                    with open(nom_complet, 'r', encoding=def_encoding ) as f:
                        contenu = f.read()
                except Exception as e:
                    #   Y'a des farceurs qui nous encodent leurs fichiers en utf 16... Faut gérer !
                    for bom in boms:
                        if contenu[:len(bom)] == bom:
                            logger.debug('{0} encodé en {1}'.format(nom_complet, boms[bom]))
                            with open(nom_complet, 'r', encoding=boms[bom]) as f:
                                try:
                                    contenu = f.read()
                                except Exception as e:
                                    logger.warning('Pas pu lire le contenu du fichier {0} en {1} pour y chercher l\'expression régulière'.format(nom_complet, boms[bom]))
                            break

                if not re.search(texte_cherche, contenu):
                    logger.debug('%s éliminé parce qu\'il ne contient pas l\'expression régulière indiquée' % nom_complet)
                    continue

            yield D, fic, taille, date_mod

