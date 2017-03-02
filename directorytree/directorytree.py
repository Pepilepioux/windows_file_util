#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
    Affiche ou exporte dans un fichier une vue arborescente d'un répertoire. Avec ou sans les fichiers.

    Version 2 2017-02-28
        L'export peut se faire dans un fichier texte simple OU au format HTML.
        Et si c'est dans un fichier html on l'ouvre automatiquement.

"""
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter.filedialog import askdirectory
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import showerror
from tkinter.messagebox import showinfo

import os
import sys
import configparser
import logging
import logging.handlers
import locale
import inspect
import winreg
import subprocess

VERSION = '2.0'
logger = logging.getLogger()
suivi = ' |  '  # Pour une jolie mise en forme


class FichierSortie():
    def __init__(self, nom_fichier, suivi=' |  ', gui=None):
        self.nom_fichier = nom_fichier
        self.numero = 0
        self.htm = True if os.path.splitext(self.nom_fichier)[1].lower() in ['.htm', '.html'] else False
        self.arborescence = ''
        self.suivi = suivi
        self.gui = gui
        self.html_debut = \
            """<!DOCTYPE html>
            <html lang="fr">
            <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>
            Arborescence répertoire
            </title>
            <style>
            body
            {
                font-family: Verdata, Arial, Helvetica, sans-serif;
                color: #000000;
                text-decoration: none;
                font-weight: normal;
                padding: 20px;
                background-color: #FFF8F0	;
            }

            h1
            {
                text-align	: center	;
                font-size	: 1.5em	;
            }

            h2
            {
                font-size	: 1.3em	;
            }

            h3
            {
                font-size	: 1.1em	;
                margin-left	: 1em	;
            }

            h4
            {
                font-size	: 1em	;
                margin-left	: 2em	;
            }


            .tx
            {
            }

            .fic
            /*	fichier	*/
            {
                margin-top : 0;
                margin-bottom : 0;

            /*
                margin-top : -0.5px;
                margin-bottom : -0.5px;
                padding-top : 0px;
                padding-bottom : 0px;
            */
            }

            .dir
            /*	Répertoire	*/
            {
                font-size : 1.1em;
                font-weight : bold;
                margin-top : 0.5em;
                margin-bottom : 0.5em;
            }

            .LR
            /*	Liste Répertoires...	*/
            {
            margin-left	: 3em	;
            margin-top	: 0.2em	;
            margin-bottom	: 0.5em	;
            /*
                border	: thin solid blue	;
            */
            }

            a.LienDiscret:link,
            a.LienDiscret:visited
            {
                color	: #000	;
                text-decoration	: none	;
            }


            a.LienDiscret:hover
            {
                color	: #00f	;
                text-decoration	: underline	;
            }


            a img
            {
            border	: none	;
            }
            </style>
            </head>
            <body>
            <script type="text/javascript">
            function	Bascule	( ielem	)
            {
            var	elem1	= 'R' + ielem	;
            var	elem2	= 'Plus' + ielem	;
            var	elem3	= 'Moins' + ielem	;
            // Quel est l'état actuel ?
            etat	= document.getElementById(elem1).style.display;

            if	(	etat	== "none"	)
                {
                document.getElementById(elem1).style.display="";
                document.getElementById(elem3).style.display="";
                document.getElementById(elem2).style.display="none";
                }
            else
                {
                document.getElementById(elem2).style.display="";
                document.getElementById(elem1).style.display="none";
                document.getElementById(elem3).style.display="none";
                }
            }
            //-------------------------------------------------------

            Event.observe(window, 'load', function() {
                $$('div.LR p a.lf').invoke('observe', 'mouseup', function(event) {

                    new Ajax.Request(
                        '../maj_bdd/maj_bdd.php',
                        {
                            method: 'get',
                            parameters: {Texte : Event.element(event).href , Session: "10173" }
                        }
                    );

                }.bindAsEventListener());
            });

            </script>

            <noscript>
            <p style="text-align:center;color:red;">
            <strong>Non, sérieusement, vous devriez <em>vraiment</em> activer le javascript...</strong>
            </p>
            <p>
            (sinon les petits "+" qui servent à sélectionner ce que vous cherchez ne marchent pas)
            </p>
            </noscript>

            <h1>
            Arborescence répertoire
            </h1>

            """
        self.html_fin = \
            """

            </div>
            </body></html>
            """
        self.listeHives = {winreg.HKEY_CLASSES_ROOT: 'HKEY_CLASSES_ROOT',
                           winreg.HKEY_CURRENT_CONFIG: 'HKEY_CURRENT_CONFIG',
                           winreg.HKEY_CURRENT_USER: 'HKEY_CURRENT_USER',
                           winreg.HKEY_LOCAL_MACHINE: 'HKEY_LOCAL_MACHINE',
                           winreg.HKEY_USERS: 'HKEY_USERS'
                           }

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------
    def __directory_tree_texte__(self, nomRepBase, fichiers_aussi, niveau=0, resultat=''):
        if self.gui:
            self.gui.stat_bar.set('%s', nomRepBase)

        if niveau is 0:
            #   Oui, c'est quand même plus joli si on rappelle le répertoire de tête...
            d = nomRepBase.upper() if fichiers_aussi else nomRepBase
            resultat = '{0}\n'.format(d)
            niveau += 1

        liste = [(1 if os.path.isdir(os.path.join(nomRepBase, e)) else 0, e)
                 for e in os.listdir(nomRepBase)
                 if (os.path.isdir(os.path.join(nomRepBase, e)) or fichiers_aussi)
                 ]
        liste.sort(key=lambda le: [le[0], le[1].upper()])

        for e in liste:
            if e[0]:
                #   C'est un répertoire. On l'imprime et on récurse
                #   Et si on imprime aussi les fichiers on met une ligne séparatrice
                #   avant chaque répertoire pour faire joli.
                ligne_vide = (self.suivi * niveau) + '\n' if fichiers_aussi else ''
                d = e[1].upper() if fichiers_aussi else e[1]
                resultat += '{0}{1}{2}\n'.format(ligne_vide, (self.suivi * niveau), d)
                resultat += self.__directory_tree_texte__(os.path.join(nomRepBase, e[1]), fichiers_aussi, niveau + 1)
            else:
                #   C'est un fichier. On l'imprime
                if fichiers_aussi:
                    #   ...oui, enfin, si c'est demandé.
                    resultat += '{0} {1}\n'.format((self.suivi * niveau), e[1].lower())

        return resultat

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------
    def __ecrire_repertoire_html__(self, nom, fichiers_aussi, niveau, expanse):
        texte = ''

        txt = '<p class="dir"><a href="javascript:Bascule(\'%s\');" class="LienDiscret">\n'
        if expanse:
            txt += '<span id="Plus%s" style="display: none;">&nbsp;+&nbsp;</span>\n'
            txt += '<span id="Moins%s">&nbsp;-&nbsp;</span>\n'
            txt += '&nbsp;%s</a></p>\n<div class="LR" id="R%s">\n'
        else:
            txt += '<span id="Plus%s">&nbsp;+&nbsp;</span>\n'
            txt += '<span id="Moins%s" style="display: none;">&nbsp;-&nbsp;</span>\n'
            txt += '&nbsp;%s</a></p>\n<div class="LR" style="display: none;" id="R%s">\n'

        texte += txt % (self.numero, self.numero, self.numero, nom, self.numero)
        self.numero += 1

        return texte

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------
    def __ecrire_fichier_html__(self, nom, niveau):
        if self.htm:
            texte = '<p class="fic">%s</p>\n' % nom
        else:
            texte = '{0} {1}\n'.format((self.suivi * niveau), nom.lower())

        return texte

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------
    def __directory_tree_html__(self, nomRepBase, fichiers_aussi, niveau=0):
        if self.gui:
            self.gui.stat_bar.set('%s', nomRepBase)

        resultat = ''
        niveau_initial = niveau
        #   Parce que si on entre au niveau 0 on sort au niveau 1...

        if niveau is 0:
            #   Oui, c'est quand même plus joli si on rappelle le répertoire de tête...
            resultat += self.__ecrire_repertoire_html__(nomRepBase, fichiers_aussi, niveau, True)
            niveau += 1
            #   self.numero += 1

        expanse = True if niveau is 0 or not fichiers_aussi else False
        #   Pour dire comment on présentera lesrépertoires par défaut

        liste = [(1 if os.path.isdir(os.path.join(nomRepBase, e)) else 0, e)
                 for e in os.listdir(nomRepBase)
                 if (os.path.isdir(os.path.join(nomRepBase, e)) or fichiers_aussi)
                 ]

        liste.sort(key=lambda le: [le[0] * -1, le[1].upper()])
        #   Oui, comme en html les répertoires sont repliables (et repliés par défaut) on les affiche en premier...

        for e in liste:
            if e[0]:
                #   C'est un répertoire. On l'imprime et on récurse
                #   Et si on imprime aussi les fichiers on met une ligne séparatrice
                #   avant chaque répertoire pour faire joli.
                d = e[1].upper() if fichiers_aussi and not self.htm else e[1]
                resultat += self.__ecrire_repertoire_html__(os.path.join(nomRepBase, e[1]), fichiers_aussi, niveau, expanse)
                #   self.numero += 1

                resultat += self.__directory_tree_html__(os.path.join(nomRepBase, e[1]), fichiers_aussi, niveau + 1)
                resultat += '</div>\n'
                #   Le self.__ecrire_repertoire_html__ a ouvert un <div>. Il faut le fermer

            else:
                #   C'est un fichier. On l'imprime
                if fichiers_aussi:
                    #   ...oui, enfin, si c'est demandé.
                    resultat += self.__ecrire_fichier_html__(e[1], niveau)

        if niveau_initial is 0:
            resultat += '</div>\n'

        return resultat

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------
    def charger_arborescence(self, repertoire, fichiers_aussi):
        self.numero = 0
        self.arborescence = self.__directory_tree_html__(repertoire, fichiers_aussi) if self.htm \
            else self.__directory_tree_texte__(repertoire, fichiers_aussi)

        return self.arborescence

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------
    def lire_arborescence(self):
        return self.arborescence

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------
    def ecrire_arborescence(self):
        F = open(self.nom_fichier, 'w', encoding='utf-8')
        if self.htm:
            F.write(self.html_debut)

        F.write(self.arborescence)

        if self.htm:
            F.write(self.html_fin)

        F.close()
        return True
        #   On verra plus tard avec le retour d'expérience s'il y a des erreurs à traiter

    # ------------------------------------------------------------------------------------
    def __lireCleRegistre__(self, hive, branche, cle):
        texteErreur = ''
        valeur = None
        typevaleur = None

        try:
            key = winreg.OpenKey(hive, branche, 0, winreg.KEY_READ)

        except:
            texteErreur = 'Erreur ouverture branche %s\\%s' % (self.listeHives[hive], branche)

        if texteErreur == '':
            try:
                (valeur, typevaleur) = winreg.QueryValueEx(key, cle)

            except:
                texteErreur = 'Erreur lecture clé %s\\%s\\%s' % (self.listeHives[hive], branche, cle)

            winreg.CloseKey(key)

        return valeur if not texteErreur else None

    # ------------------------------------------------------------------------------------
    def ouvrir_URL(self, url):
        cdeNavigateur = self.__lireCleRegistre__(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Classes\\http\\shell\\open\\command', '')

        if cdeNavigateur is None:
            # Si on ne trouve pas le défaut pour l'utilisateur on cherche ailleurs...
            cdeNavigateur = self.__lireCleRegistre__(winreg.HKEY_CLASSES_ROOT, r'http\shell\open\command', '')

        if cdeNavigateur is None:
            # ...et encore ailleurs.
            cdeNavigateur = self.__lireCleRegistre__(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Classes\http\shell\open\command', '')

        if cdeNavigateur is None:
            return False

        commande = cdeNavigateur.replace('%1', '%s' % url)
        subprocess.Popen(commande)
        return True


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
class StatusBar(tk.Frame):

    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.label = tk.Label(self, bd=1, relief=tk.SUNKEN, anchor='w')
        self.label.pack(fill=tk.X)

    def set(self, format, *args):
        self.label.config(text=format % args)
        self.label.update_idletasks()

    def clear(self):
        self.label.config(text="")
        self.label.update_idletasks()


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
class FenetrePrincipale():
    logger = logging.getLogger()

    def __init__(self):
        #   Frame.__init__(self)
        self.MAXCOLS = 5
        self.window = tk.Tk()
        self.fichiers_aussi = tk.IntVar()
        self.window.minsize(width=450, height=160)

        self.imageRepertoire = tk.PhotoImage(file='directorytree_repertoire.png')
        self.nomFichierSortie = ''

        self.window.wm_iconbitmap('directorytree.ico')
        self.window.title("Impression arborescence")

        ligne = 0
        self.lblEntree = tk.Label(self.window, text="Répertoire de tête :", bd=3, name='lblEntree')
        self.lblEntree.grid(row=ligne, column=0, sticky='nw', padx=4, pady=4)

        self.txtEntree = tk.Entry(self.window, width=30, bd=3, name='txtEntree')
        self.txtEntree.grid(row=ligne, column=1, padx=4, pady=4, sticky='new', columnspan=self.MAXCOLS - 2)

        self.boutonEntree = tk.Button(self.window, image=self.imageRepertoire, command=self.ouvrirEntree, width=50, height=26, bd=3, name='boutonEntree')
        self.boutonEntree.grid(row=ligne, column=self.MAXCOLS - 1, padx=4, pady=4, sticky='ne')

        ligne += 1
        self.lblSortie = tk.Label(self.window, text="Fichier pour résultats :", bd=3, name='lblSortie')
        self.lblSortie.grid(row=ligne, column=0, sticky='nw', padx=4, pady=4)

        self.txtSortie = tk.Entry(self.window, width=30, bd=3, name='txtSortie')
        self.txtSortie.grid(row=ligne, column=1, padx=4, pady=4, sticky='new', columnspan=self.MAXCOLS - 2)

        self.boutonSortie = tk.Button(self.window, image=self.imageRepertoire, command=self.ouvrirSortie, width=50, height=26, bd=3, name='boutonSortie')
        self.boutonSortie.grid(row=ligne, column=self.MAXCOLS - 1, padx=4, pady=4, sticky='ne')

        ligne += 1
        self.boutonFichiersAussi = tk.Checkbutton(self.window, text="Imprimer aussi le détail des fichiers", variable=self.fichiers_aussi)
        self.boutonFichiersAussi.grid(row=ligne, column=1, sticky='nw', padx=4, pady=2)

        ligne += 1
        self.texteResultat = []
        self.txtResultat = scrolledtext.ScrolledText(self.window, bd=3, name='txtResultat')
        self.ligneTxtResultat = ligne
        """
        self.txtResultat.grid(row=ligne, column=0, sticky='nsew', columnspan=self.MAXCOLS)
        self.txtResultat.delete('0.0')
        """

        ligne += 1
        self.boutonOK = tk.Button(self.window, text="Exécuter", command=self.lancerTraitement, width=10, bd=3, name='boutonOK', default='normal')
        self.boutonOK.grid(row=ligne, column=0, sticky='sw', padx=4, pady=4)

        self.lblVersion = tk.Label(self.window, text="Version " + VERSION, bd=3, name='lblVersion', font='arial 8 normal italic')
        self.lblVersion.grid(row=ligne, column=1, sticky='sew', padx=4, pady=4)

        self.boutonFin = tk.Button(self.window, text="Quitter", command=self.fini, width=10, bd=3, name='boutonFin')
        self.boutonFin.grid(row=ligne, column=self.MAXCOLS - 1, sticky='se', padx=4, pady=4)

        ligne += 1
        self.stat_bar = StatusBar(self.window)
        self.stat_bar.grid(row=ligne, column=0, sticky='nsew', columnspan=self.MAXCOLS)

        self.window.bind('<Return>', self.OnPressEnter)
        self.window.bind('<Escape>', self.OnPressEscape)

        self.window.rowconfigure(3, weight=1)
        self.window.columnconfigure(1, weight=1)
        self.txtEntree.focus_set()

    # ----------------------------------------------------------------------------------
    def ouvrirEntree(self):

        nomFic = askdirectory(title='Répertoire à parcourir')

        self.txtEntree.delete(0, tk.END)
        self.txtEntree.insert(0, nomFic)

    # ----------------------------------------------------------------------------------
    def ouvrirSortie(self):

        nomFic = asksaveasfilename(filetypes=(("Fichiers texte", "*.txt"),
                                              ("Tous les fichiers", "*.*")),
                                   #  initialdir=self.repertoireDefaut,
                                   title='Fichier des résultats')

        self.txtSortie.delete(0, tk.END)
        self.txtSortie.insert(0, nomFic)

    # ----------------------------------------------------------------------------------
    def lancerTraitement(self):
        logger.debug('lancerTraitement')
        self.nomRepertoire = self.txtEntree.get()

        #   Quelques petitesvérifications élémentaires...
        if self.nomRepertoire == '':
            messagebox.showerror('Erreur', 'Indiquer un répertoire à parcourir')
            self.txtEntree.focus_set()
            return

        if not os.path.isdir(self.nomRepertoire):
            texte = '%s n\'est pas un répertoire, ou vous n\'avez pas le droit d\'y accéder' % self.nomRepertoire
            messagebox.showerror('Erreur', texte)
            self.txtEntree.focus_set()
            return

        self.nomFichierSortie = self.txtSortie.get()
        if self.nomFichierSortie:
            try:
                (open(self.nomFichierSortie, 'w')).close()

            except PermissionError:
                texte = 'Vous n\'avez pas le droit d\'écrire dans ce répertoire,\n%s' % self.nomFichierSortie
                messagebox.showerror('Erreur', texte)
                return

            except FileNotFoundError:
                texte = 'Répertoire inexistant,\n%s' % self.nomFichierSortie
                messagebox.showerror('Erreur', texte)
                return

            except Exception as excpt:
                texte = 'Erreur %s' % excpt
                messagebox.showerror('Erreur', texte)
                return

        #   Là c'est bon, on peut y aller.
        extension = os.path.splitext(self.nomFichierSortie)[1].lower()
        self.htm = True if extension in ['.htm', '.html'] else False

        """
        texte = self.directory_tree(self.nomRepertoire, self.fichiers_aussi.get(), htm=self.htm)
        """
        F = FichierSortie(self.nomFichierSortie, gui=self)
        texte = F.charger_arborescence(self.nomRepertoire, self.fichiers_aussi.get())

        self.stat_bar.set('%s', '')

        if self.nomFichierSortie:
            """
            f = open(self.nomFichierSortie, 'w')
            f.write(texte)
            f.close()
            """
            F.ecrire_arborescence()
            if F.htm:
                F.ouvrir_URL(self.nomFichierSortie)
            messagebox.showinfo('Information', 'Arborescence de %s inscrite dans %s' % (self.nomRepertoire, self.nomFichierSortie))
        else:
            self.txtResultat.delete(0.0, tk.END)
            self.txtResultat.insert(0.0, texte)
            self.txtResultat.grid(row=self.ligneTxtResultat, column=0, sticky='nsew', columnspan=self.MAXCOLS)

        return

    # ----------------------------------------------------------------------------------
    def OnPressEnter(self, event):
        self.lancerTraitement()

    # ----------------------------------------------------------------------------------
    def OnPressEscape(self, event):
        self.fini()

    # ----------------------------------------------------------------------------------
    def fini(self):
        logger.info('Fin du programme\n')
        sys.exit()

    def run(self):
        self.window.mainloop()


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
def LireParametres():
    if hasattr(sys, 'frozen'):
        Fpgm = sys.executable
    else:
        Fpgm = os.path.realpath(__file__)

    rep = os.path.dirname(Fpgm)
    nom = os.path.splitext(os.path.basename(Fpgm))[0]

    nomFichierIni = os.path.join(rep, nom) + '.ini'
    nomFichierLog = os.path.join(rep, nom) + '.log'
    nomFichierIco = os.path.join(rep, nom) + '.ico'

    config = configparser.RawConfigParser()
    config.read(nomFichierIni)

    try:
        niveauLog = int(config.get('General', 'NiveauLog'))
    except:
        niveauLog = 0

    return nomFichierLog, niveauLog


# ------------------------------------------------------------------------------------
def creer_logger(nomFichierLog, niveauLog):
    """
        Je l'avais, je le garde... Pas sûr que ce soit VRAIMENT très utile.
    """
    logger = logging.getLogger()
    logger.setLevel(niveauLog)
    formatter = logging.Formatter('%(asctime)s	%(levelname)s	%(message)s')
    Handler = logging.handlers.WatchedFileHandler(nomFichierLog)
    Handler.setLevel(logging.DEBUG)
    Handler.setFormatter(formatter)
    Handler.set_name('Normal')
    logger.addHandler(Handler)


# -----------------------------------------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    logger = logging.getLogger()
    nomFichierLog, niveauLog = LireParametres()

    locale.setlocale(locale.LC_ALL, '')
    if niveauLog:
        creer_logger(nomFichierLog, niveauLog)

    logger.info('Début du programme')

    gui = FenetrePrincipale()
    gui.run()

    logger.info('Fin du programme\n')
