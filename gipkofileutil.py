#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
    Divers utilitaires pour les fichiers windows.


"""
import win32com.client

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
