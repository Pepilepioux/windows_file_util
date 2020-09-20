#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
    Test de remplissage des disques d'un ensempble de serveurs.

    Ce programme détermine l'espace disponible sur les disques indiqués dans le fichier .ini.
    Si cet espace devient trop faible (en fonction des paramètres indiqués dans le fichier .ini)
    il envoie un message aux destinataires indiqués.

    Il inscrit le résultat complet de ses recherches dans le fichier surveillance_espace_disque.log.
    ATTENTION, ce fichier log est en mode "append", il faut penser à le purgeg manuellement de temps en temps.

    Contenu du fichier ini :

    [General]
    #   Facultatif.
    #   NiveauLog : 10 = debug, 20 = info (par défaut), 40 = erreur, 50 = critique / fatal


    [Repertoire]
    #   Obligatoire.
    #   Liste des disques à surveiller, séparés par des virgules. Disques locaux ou réseau.
    #   Attention, pour les lettres de disque NE PAS METTRE ":\"
    disques = C,D,U,V,\\server04\c$,\\server04\d$,\\server04\v$,\\server12\c$,\\server12\e$,\\server12\f$

    [Seuils]
    #   Pour chacun des disques de la section précédente le seuil de remplissage qui déclenchera une
    #   alerte par mail.
    #
    #   Peut être une valeur absolue (nombre <espace> mo, mb, go, gb, to ou tb) ou un
    #   pourcentage (nombre <espace> %)
    #
    #   Valeur par défaut si non spécifié : 5 %

    \\server04\c$	= 10 %
    \\server04\d$	= 20 %
    \\server04\v$	= 20 %

    C	= 10 %
    D	= 10 %
    U	= 25 Go
    V	= 25 Go

    \\server12\c$	= 10 %
    \\server12\e$	= 50 Go
    \\server12\f$	= 50 Go

    [Messagerie]
    #
    #   Facultatif. Si l'émetteur, le serveur ou le "a" ne sont pas renseignés on n'envoie pas d'alerte
    #   par mail. C'est un peu bête...
    #
    #
    sender      Obligatoire. automate@mondomaine.net
    serveur     Obligatoire. Le serveur SMPT pour l'envoi des mels. "smtp.mondomaine.net", "serveur-exchange"...
    user        identifiant sur le serveur SMTP.
                Facultatif si l'utilisateur windows qui exécute le programme est connu sur le serveur SMTP.
                Obligatoire sinon.
    mdp         mot de passe de user
    a           Obligatoire. Destinataire des mels. "moi@mondomaine.net"
    cc          Facultatif. Destinataires à mettre en copie. "collegue@mondomaine.net,prestataire@soustraitant.com"...

"""
import argparse
import configparser
import ctypes
import locale
import logging
import logging.handlers
import os
import re
import smtplib
import socket
import string
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gipkomail
from gipkofileinfo import *

TYPE_VALEUR = 0
TYPE_POURCENT = 1
VERSION = '2.1'


#   -------------------------------------------------------------------------------------------------------------------------
class disque(object):
    logger = logging.getLogger()

    def __init__(self, chemin, limite, type):
        self.alerte = False
        self.chemin = chemin
        self.limite = limite
        self.type = type
        self.valide = os.path.isdir(self.chemin)
        self.espaceTotal = 0
        self.espaceLibre = 0
        self.espaceOccupe = 0
        self.calculerEspaces()
        self.alerte = self.etatAlerte()

    def calculerEspaces(self):
        if self.valide:
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(self.chemin), None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes))
            # ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dirname), None, None, ctypes.pointer(free_bytes))
            self.espaceTotal = total_bytes.value
            self.espaceLibre = free_bytes.value
            self.espaceOccupe = self.espaceTotal - self.espaceLibre

    def etatAlerte(self):
        if self.valide:
            if self.type == TYPE_VALEUR:
                if self.espaceLibre < self.limite:
                    self.alerte = True
            else:
                if (self.espaceLibre / self.espaceTotal) < (self.limite / 100):
                    self.alerte = True

        return self.alerte

    def __str__(self):
        #   À améliorer
        return self.chemin


#   -------------------------------------------------------------------------------------------------------------------------
def LireParametres():
    logger = logging.getLogger()
    erreurs = []
    avertissements = []

    if hasattr(sys, 'frozen'):
        Fpgm = sys.executable
    else:
        Fpgm = os.path.realpath(__file__)

    parser = argparse.ArgumentParser(description='Recherche espace disponible sur les disques. surveillance_espace_disque --doc pour voir la doc complète')
    parser.add_argument('--doc', action='count', help='Affiche la doc complète de ce module')
    parser.add_argument('--version', action='count', help='Affiche la version de ce module')
    args = parser.parse_args()

    if args.version:
        print('Version {0} du {1}'.format(VERSION, dateISO(get_file_dates(Fpgm)['m'])))
        sys.exit()

    if args.doc:
        print(__doc__)
        sys.exit()

    nomFichierIni = os.path.join(os.path.dirname(Fpgm), os.path.splitext(os.path.basename(Fpgm))[0]) + '.ini'
    nomFichierLog = os.path.join(os.path.dirname(Fpgm), os.path.splitext(os.path.basename(Fpgm))[0]) + '.log'

    config = configparser.RawConfigParser()
    config.read(nomFichierIni)

    niveau_log = config.getint('General', 'NiveauLog', fallback=20)

    try:
        repertoires = config.get('Repertoire', 'disques')
        lr = [e.strip(string.whitespace) for e in repertoires.split(',')]
    except Exception as e:
        erreurs.append('Erreur lecture disques, %s' % e)
        lr = []

    infos = {}
    tailleDefaut = 5
    typeDefaut = TYPE_POURCENT
    for r in lr:
        """
        Y'a un chni avec les lettres de disques. Le configparser ne sait pas lire les clés contenant le caractère "deux points"
        Il faudra donc ruser et ajouter le suffixe ":\" si le chemin consiste en une seule lettre
        """
        try:
            infosSeuil = config.get('Seuils', r)
        except:
            infosSeuil = None
            if re.match('^[A-Za-z]$', r):
                r += ':\\'
            infos[r] = {'taille': tailleDefaut, 'type': typeDefaut}
            avertissements.append('Erreur lecture seuils pour %s, on prend les valeurs par défaut' % r)
            continue

        if re.match('^[A-Za-z]$', r):
            r += ':\\'

        valeurLue = re.split('\s+', infosSeuil.strip())

        if len(valeurLue) != 2:
            infos[r] = {'taille': tailleDefaut, 'type': typeDefaut}
            avertissements.append('Erreur seuils pour %s, "%s", on prend les valeurs par défaut' % (r, infosSeuil))
            continue

        # On a bien deux valeurs. La première DOIT être numérique
        valeurLue[0] = valeurLue[0].replace(',', '.')
        # Puisque les américains ne sont pas foutus d'utiliser le bon séparateur décimal...
        try:
            valeurLue[0] = float(valeurLue[0])
        except:
            infos[r] = {'taille': tailleDefaut, 'type': typeDefaut}
            avertissements.append('%s n\'est pas une valeur numérique correcte, on prend les valeurs par défaut' % (valeurLue[0]))
            # print('Ligne %s' % inspect.getframeinfo(inspect.currentframe())[1])
            continue

        # print('valeurLue[1].lower() = "%s"' % valeurLue[1].lower())
        # Maintenant on a bien un nombre et une deuxième valeur
        if valeurLue[1].lower() == 'mo' or valeurLue[1].lower() == 'mb':
            infos[r] = {'taille': valeurLue[0] * 1024 * 1024, 'type': TYPE_VALEUR}
            continue

        if valeurLue[1].lower() == 'go' or valeurLue[1].lower() == 'gb':
            infos[r] = {'taille': valeurLue[0] * 1024 * 1024 * 1024, 'type': TYPE_VALEUR}
            continue

        if valeurLue[1].lower() == 'to' or valeurLue[1].lower() == 'tb':
            infos[r] = {'taille': valeurLue[0] * 1024 * 1024 * 1024 * 1024, 'type': TYPE_VALEUR}
            continue

        if valeurLue[1] == '%':
            # On teste si valeur > 100 ?
            # Bôf, non, on s'en fout, ils ont qu'à faire attention !
            infos[r] = {'taille': valeurLue[0], 'type': TYPE_POURCENT}
            continue

        # Si on arrive là c'est qu'on n'a pas réussi à décrypter
        avertissements.append('%s %s n\'est pas une valeur correcte, on prend les valeurs par défaut' % (valeurLue[0], valeurLue[1]))
        # print('Ligne %s' % inspect.getframeinfo(inspect.currentframe())[1])

    try:
        smtp_serveur = config.get('Messagerie', 'serveur')
    except Exception as e:
        avertissements.append('Erreur lecture serveur SMPT, %s' % e)
        smtp_serveur = None

    try:
        smtp_sender = config.get('Messagerie', 'sender')
    except Exception as e:
        avertissements.append('Erreur lecture sender, %s' % e)
        smtp_sender = None

    try:
        smtp_user = config.get('Messagerie', 'user')
    except Exception as e:
        avertissements.append('Erreur lecture sender, %s' % e)
        smtp_user = None

    try:
        smtp_pwd = config.get('Messagerie', 'mdp')
    except Exception as e:
        avertissements.append('Erreur lecture sender, %s' % e)
        smtp_pwd = None

    try:
        destinataire = config.get('Messagerie', 'A')
    except Exception as e:
        avertissements.append('Erreur lecture destinataire, %s' % e)
        destinataire = None

    try:
        copies = config.get('Messagerie', 'CC')
        listeCopies = copies.split(',')
    except Exception as e:
        listeCopies = []

    return infos, destinataire, listeCopies, nomFichierIni, nomFichierLog, smtp_sender, smtp_serveur, smtp_user, smtp_pwd, niveau_log, erreurs, avertissements


"""
# ------------------------------------------------------------------------------------
def EnvoyerMesage(serveur, sender, destinataire, listeCopies, subject, contenu):
    logger = logging.getLogger()
    msg = MIMEMultipart()
    msg = MIMEText(contenu)
    msg['From'] = sender
    msg['To'] = destinataire
    msg['CC'] = ','.join(listeCopies)
    msg['Subject'] = subject

    addr_from = sender
    addr_to = []
    addr_to.append(destinataire)
    addr_to += listeCopies

    s = smtplib.SMTP(serveur)
    rep = s.sendmail(addr_from, addr_to, msg.as_string())
    s.quit()


"""
# ------------------------------------------------------------------------------------
def affichageHumain(taille):
    prefixes = ['o', 'ko', 'Mo', 'Go', 'To', 'Po', 'Eo', 'Zo', 'Yo']
    facteur = 1000
    n = 0
    while taille > facteur and n < len(prefixes) - 1:
        taille = taille / facteur
        n += 1

    return '%s %s' % (locale.format_string('%3.1f', taille, True), prefixes[n])


# ------------------------------------------------------------------------------------
def creer_logger(nomFichierLog, niveauLog=logging.INFO, formatter=None):
    #   formatter = logging.Formatter('%(asctime)s	%(levelname)s	%(module)s	%(lineno)d	%(message)s')
    logger = logging.getLogger()
    logger.setLevel(niveauLog)

    if formatter is None:
        formatter = logging.Formatter('%(asctime)s	%(levelname)s	%(message)s')

    Handler = logging.handlers.WatchedFileHandler(nomFichierLog)
    Handler.setLevel(niveauLog)
    Handler.setFormatter(formatter)
    logger.addHandler(Handler)


# ------------------------------------------------------------------------------------

logger = logging.getLogger()
ts_debut = time.time()
locale.setlocale(locale.LC_TIME, '')
locale.setlocale(locale.LC_NUMERIC, 'French')

source = socket.gethostname()

# Acquisition des paramètres...
listeRepertoires, destinataire, listeCopies, nomFichierIni, nomFichierLog, smtp_sender, smtp_serveur, smtp_user, smtp_pwd, niveau_log, erreurs, avertissements = LireParametres()

creer_logger(nomFichierLog, niveauLog=niveau_log)
logger.info('Début du programme')
for e in avertissements:
    logger.warning(e)

for e in erreurs:
    logger.error(e)

if erreurs:
    logger.error('Trop d\'erreurs, impossible de continuer. Fin du programme\n')
    exit()

listeDisques = [disque(r, listeRepertoires[r]['taille'], listeRepertoires[r]['type']) for r in listeRepertoires]

contenu = ''
sujet = 'Alerte espace disque de %s' % source

for d in listeDisques:
    if d.valide:
        texte = d.chemin
        texte += '\tLibres:\t%s\tsur\t%s' % (affichageHumain(d.espaceLibre), affichageHumain(d.espaceTotal))
        texte += '\tsoit\t%s %%' % locale.format_string('%3.1f', (d.espaceLibre / d.espaceTotal) * 100, True)
        texte += '\t%s\t%s' % (d.espaceTotal, d.espaceLibre)
        if d.alerte:
            contenu += texte + '\n'
            texte += '\tALERTE !'

    else:
        texte = d.chemin + ('\t' * 8) + 'inaccessible !'

    logger.info(texte)

if contenu and smtp_sender and smtp_serveur and destinataire:
    """
            envoyer_message(serveur, sender, destinataire, subject,  contenu_texte=contenuTexte, smtp_user=smtp_user,
                    smtp_pwd=smtp_pwd, contenu_html=contenuHTML, cc=listeCopies, bcc=listeBCC, files=files)
    """
    try:
        rep = gipkomail.envoyer_message(smtp_serveur, smtp_sender, destinataire, sujet, contenu_texte=contenu, smtp_user=smtp_user, smtp_pwd=smtp_pwd, cc=listeCopies)
    except Exception as e:
        logger.error('Erreur envoi message.')
        logger.critical(e)
    else:
        if rep:
            logger.warning('Erreur(s) lors de l\'envoi des messages')
            for item in rep.items():
                logger.warning(item)

logger.info('Fin du programme\n')
exit()
