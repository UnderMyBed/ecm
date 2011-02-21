'''
This file is part of ICE Security Management

Created on 24 jan. 2010
@author: diabeteman
'''

from ism.data.corp.models import Hangar, Wallet

from django.db import models
from datetime import datetime

#------------------------------------------------------------------------------
class Member(models.Model):
    
    DIRECTOR_ACCESS_LVL = 999999999999;

    characterID = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=128, db_index=True)
    nickname = models.CharField(max_length=256, default="")
    baseID = models.BigIntegerField(db_index=True, default=0)
    corpDate = models.DateTimeField(db_index=True, default=datetime.now())
    lastLogin = models.DateTimeField(db_index=True, default=datetime.now())
    lastLogoff = models.DateTimeField(db_index=True, default=datetime.now())
    location = models.CharField(max_length=256, default="")
    ship = models.CharField(max_length=128, default="")
    accessLvl = models.PositiveIntegerField(default=0)
    corped = models.BooleanField(default=True)
    extraRoles = models.PositiveIntegerField(default=0)

    def getTitles(self):
        ids = TitleMembership.objects.filter(member=self).values_list("title", flat=True)
        return list(Title.objects.filter(titleID__in=ids))
    
    def getRoles(self, ignore_director=False):
        if ignore_director:
            ids = RoleMembership.objects.filter(member=self).exclude(role__roleID=1).values_list("role", flat=True)
        else:
            ids = RoleMembership.objects.filter(member=self).values_list("role", flat=True)
        return list(Role.objects.filter(id__in=ids))
    
    def getImpliedRoles(self):
        roles = self.getRoles()
        for t in self.getTitles():
            for r in t.getRoles():
                if r not in roles:
                    roles.append(r)
        return roles
    
    def isDirector(self):
        roles = RoleMembership.objects.filter(member=self, role__roleID=1)
        return len(roles) > 0
    
    def getAccessLvl(self):
        if self.isDirector():
            return self.DIRECTOR_ACCESS_LVL
        roles = self.getImpliedRoles()
        lvl = 0
        for r in roles: lvl += r.getAccessLvl()
        return lvl

    def getTitleChanges(self):
        return TitleMemberDiff.objects.filter(member=self).order_by("-id")
    
    def __hash__(self):
        return self.characterID

    def __eq__(self, other):
        return self.characterID == other.characterID
    
    def __cmp__(self, other):
        return cmp(self.name.lower(), other.name.lower())

    def __unicode__(self):
        return self.name


#------------------------------------------------------------------------------
class RoleType(models.Model):
    typeName = models.CharField(max_length=64, unique=True)
    dispName = models.CharField(max_length=64)
    
    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        return self.id == other.id

    def __unicode__(self):
        if self.dispName:
            return self.dispName
        else:
            return self.typeName
    
#------------------------------------------------------------------------------
class Title(models.Model):
    titleID = models.BigIntegerField(primary_key=True)
    titleName = models.CharField(max_length=256)
    members = models.ManyToManyField(Member, through='TitleMembership')
    tiedToBase = models.BigIntegerField(default=0)
    accessLvl = models.PositiveIntegerField(default=0)
    
    def getRoles(self):
        ids = TitleComposition.objects.filter(title=self).values_list("role", flat=True)
        return Role.objects.filter(id__in=ids)
        
    def getAccessLvl(self):
        roles = self.getRoles()
        lvl = 0
        for r in roles : lvl += r.getAccessLvl()
        return lvl
    
    def __hash__(self):
        return self.titleID
    
    def __eq__(self, other):
        return self.titleID == other.titleID
    
    def __unicode__(self):
        return self.titleName
    
#------------------------------------------------------------------------------
class Role(models.Model):
    roleType = models.ForeignKey(RoleType, db_index=True)
    roleID = models.IntegerField()
    roleName = models.CharField(max_length=64)
    dispName = models.CharField(max_length=64)
    members = models.ManyToManyField(Member, through='RoleMembership')
    titles = models.ManyToManyField(Title, through='TitleComposition')
    description = models.CharField(max_length=256)
    hangar = models.ForeignKey(Hangar, null=True, blank=True)
    wallet = models.ForeignKey(Wallet, null=True, blank=True)
    accessLvl = models.PositiveSmallIntegerField(default=0)
    
    def getAccessLvl(self):
        if   self.hangar: return self.hangar.accessLvl
        elif self.wallet: return self.wallet.accessLvl
        else:             return self.accessLvl
    
    def getTitles(self):
        t_compos = TitleComposition.objects.filter(role=self)
        ids = [ tc.title_id for tc in t_compos ]
        return Title.objects.filter(titleID__in=ids)
    
    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        return self.id == other.id

    def __unicode__(self):
        try:
            name = self.dispName
            if self.hangar_id :
                name = name % Hangar.objects.get(hangarID=self.hangar_id).name
            elif self.wallet_id : 
                name = name % Wallet.objects.get(walletID=self.wallet_id).name
            return "%s - %s" % (name, unicode(self.roleType))
        except:
            return self.roleName
    
    def __getattr__(self, attr_name):
        if attr_name == "name":
            return self.getDispName()
        else:
            raise AttributeError("Role has no attribute %s" % attr_name)
    
    def getDispName(self):
        try:
            name = self.dispName
            if self.hangar_id :
                name = name % Hangar.objects.get(hangarID=self.hangar_id).name
            elif self.wallet_id : 
                name = name % Wallet.objects.get(walletID=self.wallet_id).name
            return name
        except:
            return self.roleName


#------------------------------------------------------------------------------
class RoleMembership(models.Model):
    member = models.ForeignKey(Member)
    role = models.ForeignKey(Role)
    
    h = None

    def __hash__(self):
        if not self.h:
            try:    self.h = self.member.characterID * self.role.id
            except: self.h = -1
        return self.h
    
    def __eq__(self, other):
        try: return self.member == other.member and self.role == other.role
        except: return False
    
    def __unicode__(self):
        return '%s has %s (%s)' % (unicode(self.member), unicode(self.role), unicode(self.role.roleType))
    
#------------------------------------------------------------------------------
class TitleMembership(models.Model):
    member = models.ForeignKey(Member)
    title = models.ForeignKey(Title)
    
    h = None
        
    def __hash__(self):
        if not self.h:
            try:
                self.h = self.member.characterID * self.title.titleID
            except:
                self.h = -1
        return self.h
    
    def __eq__(self, other):
        try: return self.member == other.member and self.title == other.title
        except: return False
    def __unicode__(self):
        return unicode(self.member) + u' is ' + unicode(self.title)
    
#------------------------------------------------------------------------------
class TitleComposition(models.Model):
    title = models.ForeignKey(Title)
    role = models.ForeignKey(Role)
    
    h = None
    
    def __hash__(self):
        if not self.h:
            self.h = self.title.titleID + self.role.id 
        return self.h 
    
    def __eq__(self, other):
        return self.title.titleID == other.title.titleID and self.role.id == other.role.id
    
    def __unicode__(self):
        return unicode(self.title) + u' has ' + unicode(self.role)


#========================#
#  DIFF HISTORY CLASSES  #
#========================#
#------------------------------------------------------------------------------
class TitleCompoDiff(models.Model):
    title = models.ForeignKey(Title)
    role = models.ForeignKey(Role)
    # true if role is new in title, false if role was removed
    new = models.BooleanField(db_index=True, default=True)
    # date of change
    date = models.DateTimeField(db_index=True, default=datetime.now())
    
    def __unicode__(self):
        if self.new: return unicode(self.title) + u' gets ' + unicode(self.role)
        else       : return unicode(self.title) + u' looses ' + unicode(self.role)
        
#------------------------------------------------------------------------------
class MemberDiff(models.Model):
    characterID = models.BigIntegerField(db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    nickname = models.CharField(max_length=256, db_index=True)
    # true if title is new for member, false if title was removed
    new = models.BooleanField(db_index=True, default=True)
    # date of change
    date = models.DateTimeField(db_index=True, default=datetime.now())
    
    def __unicode__(self):
        if self.new: return '%s corped' % self.name
        else       : return '%s leaved' % self.name
        
#------------------------------------------------------------------------------
class TitleMemberDiff(models.Model):
    member = models.ForeignKey(Member)
    title = models.ForeignKey(Title)
    # true if title is new for member, false if title was removed
    new = models.BooleanField(db_index=True, default=True)
    # date of change
    date = models.DateTimeField(db_index=True, default=datetime.now())

    def __unicode__(self):
        if self.new: return '%s got %s' % (self.member.name, self.title.titleName)
        else       : return '%s lost %s' % (self.member.name, self.title.titleName)
    
#------------------------------------------------------------------------------
class RoleMemberDiff(models.Model):
    member = models.ForeignKey(Member)
    role = models.ForeignKey(Role)
    # true if role is new for member, false if role was removed
    new = models.BooleanField(db_index=True, default=True)
    # date of change
    date = models.DateTimeField(db_index=True, default=datetime.now())
    
    def __unicode__(self):
        if self.new: return '%s got %s' % (self.member.name, self.role.dispName)
        else       : return '%s lost %s' % (self.member.name, self.role.dispName)

