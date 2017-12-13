#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
    Divers utilitaires pour les fichiers windows.


"""
import win32com.client
import winreg

VERSION = '1.0'


#   -------------------------------------------------------------------------------
def creerRaccourci(nom, cible)	:
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(nom)
        shortcut.Targetpath = cible
        shortcut.save()
    except Exception as excpt:
        tb = None
        return excpt.with_traceback(tb)

    return ''


# ------------------------------------------------------------------------------------
def chercherProgrammeDefaut(typeFichier):
    """

        Cherche le programme utilisé par défaut pour ouvrir un type de fichier (windows uniquement)
        Renvoie la valeur trouvée dans la base de registre, du type "D\Dir\ss-dir\pgm.exe" %1, où
        %1 est le nom du fichier à ouvrir.

        J'ai trouvé deux façons d'obtenir cette info dans la base de registre, il y en a peut-être d'autres.

    """
    if typeFichier[0] != '.':
        typeFichier = '.' + typeFichier

    #   Première possibilité : il y a une appli par défaut au niveau de l'utilisateur.
    try:
        branche = r'Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\%s\\UserChoice' % typeFichier
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, branche, 0, winreg.KEY_READ)
        valeur = winreg.QueryValueEx(key, 'Progid')[0]

        branche = '%s\\shell\\open\\command' % valeur
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, branche, 0, winreg.KEY_READ)
        valeur = winreg.QueryValueEx(key, '')[0]
    except:
        valeur = None

    if valeur is None:
        #   Deuxième possibilité : il n'y a rien au niveau utilisateur, mais il y a peut-être
        #   au niveau système...
        try:
            branche = typeFichier
            key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, branche, 0, winreg.KEY_READ)
            valeur = winreg.QueryValueEx(key, '')[0]

            branche = '%s\\shell\\open\\command' % valeur
            key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, branche, 0, winreg.KEY_READ)
            valeur = winreg.QueryValueEx(key, '')[0]

        except:
            valeur = None

    return valeur
