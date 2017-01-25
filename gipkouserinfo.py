#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
    Donne des informations sur les utilisateurs et les groupes d'un serveur windows

    Utilisé en complément de gipkofileinfo si par exemple on veut connaître tous
    les droits d'un utilisateur particulier sur une arborescence

    Version 2.0 2017-01-16
        Dans les listes de groupes on ajoute le descriptif.
        La liste des groupes devient un dictionnaire, bien plus pratique pour une recherche directe par le nom.

        Attention, microsoft met des caractères à la con en unicode (!) dans certains de ses noms de groupes !

    Version 2.1 2017-01-25
        On ajoute manuellement certains noms de groupes et d'utilisateurs (voir explications dans __get_groups__)

"""

import win32net
import win32netcon
import os

VERSION = '2.1'


#   -------------------------------------------------------------------------------
class UserInfo:
    """
        Doc à continuer
    """
    def __init__(self, server=os.environ.get('LOGONSERVER')):
        self.server = server
        self.groups_list = self.__get_groups__()
        self.users_list = self.__get_users__()
        self.user_s_groups_list = self.__get_user_s_groups__()

        return

    #   -------------------------------------------------------------------------------
    def __get_groups__(self):
        """
            Renvoie un dictionnaire des groupes du serveur avec, pour chacun, la liste de ses membres et
            le descriptif.
            N.B. On met tous les noms en minuscules pour ne pas être emmerdé quand on voudra faire
            "if nom in liste"
        """
        groups_list = {}
        resume = 0
        Enr, Total, resume = win32net.NetGroupEnum(self.server, 2, resume, 4096)
        while 1:
            for Champ in Enr:
                group_name = Champ['name'].lower()
                group_comment = Champ['comment']
                members_list = []
                memberresume = 0
                memberdata, total, memberresume = win32net.NetGroupGetUsers(self.server, group_name, 1, memberresume)

                while 1:
                    for member in memberdata:
                        members_list.append(member['name'].lower())

                    if memberresume <= 0:
                        break

                    memberdata, total, memberresume = win32net.NetGroupGetUsers(self.server, group_name, 1, memberresume)

                members_list.sort()
                groups_list[group_name] = [members_list, group_comment]

            if resume <= 0:
                break

            Enr, Total, resume = win32net.NetGroupEnum(self.server, 2, resume, 4096)

        """
            Cet abruti de microsoft s'obstine à utiliser des alias pour certains noms ("c:/Utilisateurs" par exemple
            qui est en réalité c:/Users"...).
            C'est ainsi que le groupe "domain users" est parfois traduit par "utilisateurs".
            Pour pas être emmerdés on ajoute artificiellement ces noms à la con. (fruit de l'expérience ! Et c'est
            certainement pas fini. À adapter aussi en fonction de la langue)
        """
        try:
            groups_list['administrateurs'] = groups_list['domain admins']
        except:
            pass

        try:
            groups_list['utilisateurs'] = groups_list['domain users']
        except:
            pass

        return groups_list

    #   -------------------------------------------------------------------------------
    def __get_users__(self):
        """
            Renvoie un dictionnaire des utilisateurs du serveur.

            Infos disponibles :

            acct_expires        full_name           max_storage         primary_group_id
            auth_flags          home_dir            name                priv
            bad_pw_count        home_dir_drive      num_logons          profile
            code_page           last_logoff         parms               script_path
            comment             last_logon          password            units_per_week
            country_code        logon_hours         password_age        user_id
            flags               logon_self.server   password_expired    usr_comment

            N.B. On met les noms d'utilisteurs en minuscules pour ne pas être emmerdé quand on voudra faire
            "if nom in liste"
        """
        users_list = {}
        Reprise = 0
        Enr, Total, Reprise = win32net.NetUserEnum(self.server, 3, win32netcon.FILTER_NORMAL_ACCOUNT, Reprise, 1)

        while Reprise > 0:
            for Champ in Enr:
                users_list[Champ['name'].lower()] = [Champ['full_name'], Champ['comment'], Champ['usr_comment'], Champ['user_id']]

            Enr, Total, Reprise = win32net.NetUserEnum(self.server, 3, win32netcon.FILTER_NORMAL_ACCOUNT, Reprise, 1)

        if 'système' not in users_list:
            users_list['système'] = ['Système', 'Système', '', 0]

        return users_list

    #   -------------------------------------------------------------------------------
    def __get_user_s_groups__(self):
        """
            Renvoie un dictionnaire contenant pour chaque utilisateur la liste des groupes auxquel il appartient.
        """
        dict = {}
        for g in self.groups_list:
            # Le nom du groupe est la clé du dictionnaire. La liste des membres est le premier élément de la liste.

            for u in self.groups_list[g][0]:
                if u in dict:
                    dict[u].append(g)
                else:
                    dict[u] = [g]

        """
            Une horrible verrue est nécessaire :
            pour microsoft tous les utilisateurs appartiennent au groupe... "Tout le monde" (!), mais
            ce groupe n'apparaît pas dans la liste renvoyée par win32net.NetGroupEnum.
            Il faut donc le rajouter à la main.
            Faudra voir comment ça marche dans les autres langues...

            Idem avec le groupe "users" :
            Les groupes intégrés ont des affichages farfelus en fonction de l'interface.
            Le même groupe s'affiche "Domaine\\Users" dans la fenêtre windows, "BUILTIN\\Utilisateurs"
            dans une fenêtre DOS (et ça, évidemment, ça change avec la langue de l'installation...),
            et "Domain Users" quand on appelle win32net.NetGroupGetUsers...
            Et on n'est pas à l'abri de nouvelles découvertes !
        """
        for u in dict:
            dict[u].append('tout le monde')

            if 'domain users' in dict[u]:
                dict[u].append('utilisateurs')

            # Parce que je suis maniaque, et pour une meilleure lisibilité humaine au besoin
            dict[u].sort()

        return dict

    #   -----------------------------------------------------------------------
    def __get_local_groups__(self):
        """
            En prévision de l'avenir.
            Sur une machine qui n'est pas contrôleur de domaine la fonction NetGroupEnum ramène un seul groupe qui
            d'appelle "None".

            On verra plus tard comment traiter ça.
                Un indicateur serveur AD / pas serveur AD ?
                On appelle ça de façon transparente si on se rend compte qu'on n'est pas sur un serveur AD ?
                On ajoute les groupes locaux aux groupes globaux si on est sur un un serveur AD ?
        """
        groups_list = []
        resume = 0
        Enr, Total, resume = win32net.NetLocalGroupEnum(self.server, 1, resume, 4096)
        while 1:
            for Champ in Enr:
                group_name = Champ['name'].lower()
                members_list = []
                memberresume = 0
                memberdata, total, memberresume = win32net.NetLocalGroupGetMembers(self.server, group_name, 1, memberresume)

                while 1:
                    for member in memberdata:
                        members_list.append(member['name'].lower())

                    if memberresume <= 0:
                        break

                    memberdata, total, memberresume = win32net.NetLocalGroupGetMembers(self.server, group_name, 1, memberresume)

                members_list.sort()
                groups_list.append([group_name, members_list])

            if resume <= 0:
                break

            Enr, Total, resume = win32net.NetLocalGroupEnum(self.server, 1, resume, 4096)

        return groups_list

    #   -------------------------------------------------------------------------------
    def get_users(self):
        return self.users_list

    #   -------------------------------------------------------------------------------
    def get_groups(self):
        return self.groups_list

    #   -------------------------------------------------------------------------------
    def get_user_s_groups(self, user):
        try:
            return self.user_s_groups_list[user.lower()]
        except KeyError:
            return None
