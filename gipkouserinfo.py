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

    Version 2.2 2017-02-15
        On ajoute les "flags" de l'utilisateur. Ces flags sont :
        UF_SCRIPT                            1
        UF_ACCOUNTDISABLE                    2
        UF_HOMEDIR_REQUIRED                  8
        UF_LOCKOUT                          16
        UF_PASSWD_NOTREQD                   32
        UF_PASSWD_CANT_CHANGE               64
        UF_TEMP_DUPLICATE_ACCOUNT          256
        UF_NORMAL_ACCOUNT                  512
        UF_INTERDOMAIN_TRUST_ACCOUNT      2048
        UF_WORKSTATION_TRUST_ACCOUNT      4096
        UF_SERVER_TRUST_ACCOUNT           8192
        UF_MACHINE_ACCOUNT_MASK          14336
        UF_ACCOUNT_TYPE_MASK             15104
        UF_DONT_EXPIRE_PASSWD            65536
        UF_MNS_LOGON_ACCOUNT            131072
        UF_SETTABLE_BITS                211835

        On ajoute aussi la méthode "user_disabled". Les autres... On verra au fur et à mesure des besoins

    Version 3.0 2017-02-16
        Le win32net.NetGroupGetUsers ne renvoie QUE les utilisateurs, pas les groupes !
        Donc si on veut traiter les groupes imbriqués il faut prendre une autre méthode.
        J'ai trouvé un truc qui va bien sur
        http://code.activestate.com/recipes/498096-recursively-look-up-groups-in-active-directory/
        http://www.sourcecodeonline.com/details/recursively_look_up_groups_in_active_directory.html

        Le get_groups renvoie maintenant pour chaque groupe deux listes de membres :
        - la liste complète des users, en décortiquant récursivement les sous-groupes, et
        - une liste "brute" des membres dont chaque élément est une liste contenant le nom
          du membre et l'indication User/Group

    Version 3.1 2017-02-22
        Ajouté une liste des SID par utilisateur.

    Version 3.2 2017-12-19
        Ajouté la propriété get_users_dict, dictionnaire par utilisateur de toutes les propriétés.

"""

import win32net
import win32netcon
import os
import sys
import win32security
from win32com.client import *

VERSION = '3.2'


#   -------------------------------------------------------------------------------
class UserInfo:
    """
        Doc à continuer
    """
    def __init__(self, server=os.environ.get('LOGONSERVER')):
        self.server = server.replace('\\', '')

        #   Version 3.0
        self.attribs = "name,member,objectClass,adspath,primaryGroupToken,primaryGroupID,description"
        self.objConnection = Dispatch("ADODB.Connection")
        self.objConnection.Open("Provider=ADsDSOObject")

        ldap_root = GetObject('LDAP://%s/rootDSE' % self.server)
        self.dn = ldap_root.Get('defaultNamingContext')
        self.groups_names = self.__get_groups_names__()
        #   Fin Version 3.0

        self.groups_list = self.__get_groups__()
        self.users_list, self.users_dict = self.__get_users__()
        self.user_s_groups_list = self.__get_user_s_groups__()
        self.sids_list = self.__get_sids__()

        return

    #   -------------------------------------------------------------------------------
    def __get_groups_V0__(self):
        """

            Version précédente. Je la garde pour conjurer le mauvais sort

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
            groups_list['administrators'] = groups_list['domain admins']
        except:
            pass

        try:
            groups_list['utilisateurs'] = groups_list['domain users']
        except:
            pass

        try:
            groups_list['users'] = groups_list['domain users']
        except:
            pass

        return groups_list

    #   -------------------------------------------------------------------------------
    def __get_primary_group_members__(self, token):
        """

            Crédit : voir dans la doc d'en-tête à la rubrique "Version 3"

            Used to look up Users whose Primary Group is set to one of the groups we're
            looking up.  This is necessary as AD uses that attribute to calculate a group's
            membership.  These type of users do not show up if you query the group's member field
            directly.

            searchRoot is the part of the LDAP tree that you want to start searching from.
            token is the groups primaryGroupToken.
        """
        strSearch = \
            "<LDAP://%s>;(primaryGroupID=%d);name;subtree" % \
            (self.dn, token)
        objRecordSet = self.objConnection.Execute(strSearch)[0]
        memberList = []

        # Process if accounts are found.
        if objRecordSet.RecordCount > 0:
            objRecordSet.MoveFirst()

            while not objRecordSet.EOF:
                memberList.append(objRecordSet.Fields[0].Value)
                # memberList.append("%s%s" % (header, objRecordSet.Fields[0].Value))
                objRecordSet.MoveNext()

        # Return the list of results
        return memberList

    #   -------------------------------------------------------------------------------
    def __get_group_members__(self, group_name, recurse=False):
        strSearch = \
            "<LDAP://%s>;(&(objectCategory=%s)(sAMAccountName=%s));%s;subtree" % \
            (self.dn, 'Group', group_name, self.attribs)
        objRecordSet = self.objConnection.Execute(strSearch)[0]

        # Normally, we would only expect one object to be retrieved.
        if objRecordSet.RecordCount == 1:
            # Set up a dictionary with attribute/value pairs and return the dictionary.
            for f in objRecordSet.Fields:
                liste_pg = []
                if f.Name == 'member':
                    liste = [cn.split('=')[1].lower() for cn in [e.split(',')[0] for e in f.Value]] if f.Value is not None else []
                    # break

                if f.Name == 'primaryGroupToken':
                    liste_pg = self.__get_primary_group_members__(f.Value)

            membres = liste_pg
            for e in liste:
                if e in self.groups_names:
                    if recurse:
                        membres += self.__get_group_members__(e, recurse)
                    else:
                        membres.append([e, 'g'])
                else:
                    membres.append([e, 'u'])

            if recurse:
                membres.sort()
                for i in range(len(membres) - 1, 1, -1):
                    if membres[i] == membres[i - 1]:
                        membres.remove(membres[i])

            else:
                #   On met les groupes en premier
                membres.sort(key=lambda x: x[1])

            return membres
        else:
            # Group not found
            return []

    #   -------------------------------------------------------------------------------
    def __get_groups_names__(self):
        """
            Renvoie la liste des noms des groupes du serveur.
            On a besoin de cette liste simple pour remplir la liste complète des groupes avec leurs membres, dans la
            recherche récursive des utilisateurs appartenant indirectement au groupe.
        """
        groups_names = []
        resume = 0
        Enr, Total, resume = win32net.NetGroupEnum(self.server, 2, resume, 4096)
        while 1:
            for Champ in Enr:
                groups_names.append(Champ['name'].lower())

            if resume <= 0:
                break

            Enr, Total, resume = win32net.NetGroupEnum(self.server, 2, resume, 4096)

        return groups_names

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

                # members_list = self.__get_group_members__(group_name)
                users_list = [e[0] for e in self.__get_group_members__(group_name, True)]
                members_list = [e for e in self.__get_group_members__(group_name, False)]
                groups_list[group_name] = [users_list, group_comment, members_list]

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
            groups_list['administrators'] = groups_list['domain admins']
        except:
            pass

        try:
            groups_list['utilisateurs'] = groups_list['domain users']
        except:
            pass

        try:
            groups_list['users'] = groups_list['domain users']
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
        users_dict = {}
        Reprise = 0
        Enr, Total, Reprise = win32net.NetUserEnum(self.server, 3, win32netcon.FILTER_NORMAL_ACCOUNT, Reprise, 1)

        while Reprise > 0:
            for Champ in Enr:
                users_list[Champ['name'].lower()] = [Champ['full_name'], Champ['comment'], Champ['usr_comment'], Champ['user_id'], Champ['flags']]
                users_dict[Champ['name'].lower()] = {cle: Champ[cle] for cle in Champ if cle != 'name'}

            Enr, Total, Reprise = win32net.NetUserEnum(self.server, 3, win32netcon.FILTER_NORMAL_ACCOUNT, Reprise, 1)

        if 'système' not in users_list:
            users_list['système'] = ['Système', 'Système', '', 0, 4260353]

        return users_list, users_dict

    #   -------------------------------------------------------------------------------
    def __get_sids__(self):
        """
            Renvoie un dictionnaire des sid par utilisateur.
        """
        sids_list = {}
        for u in self.users_list:
            try:
                sid, D, T = win32security.LookupAccountName('', u)
                sids_list[u] = sid
            except:
                pass

        for g in self.groups_list:
            try:
                sid, D, T = win32security.LookupAccountName('', g)
                sids_list[g] = sid
            except:
                #   Certains groupes, comme ceux qui ont été traduits, ne seront pas trouvés.
                pass

        return sids_list

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
    def get_users_dict(self):
        return self.users_dict

    #   -------------------------------------------------------------------------------
    def get_sids(self):
        return self.sids_list

    #   -------------------------------------------------------------------------------
    def get_groups(self):
        return self.groups_list

    #   -------------------------------------------------------------------------------
    def get_user_s_groups(self, user):
        try:
            return self.user_s_groups_list[user.lower()]
        except KeyError:
            return {}

    #   -------------------------------------------------------------------------------
    def user_disabled(self, user):
        try:
            return(self.users_list[user][4] & win32netcon.UF_ACCOUNTDISABLE)
        except:
            return win32netcon.UF_ACCOUNTDISABLE
