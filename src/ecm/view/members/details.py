# The MIT License - EVE Corporation Management
# 
# Copyright (c) 2010 Robin Jarry
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

__date__ = "2011-03-13"
__author__ = "diabeteman"


import json

from django.shortcuts import render_to_response
from django.views.decorators.cache import cache_page
from django.template.context import RequestContext
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from ecm.core import utils
from ecm.data.roles.models import MemberDiff, Member, RoleMemberDiff, TitleMemberDiff
from ecm.view import getScanDate
from ecm.data.common.models import ColorThreshold
from ecm.core.utils import print_time_min, get_access_color
from ecm.core.db import resolveLocationName
from ecm.core.auth import user_owns_character


#------------------------------------------------------------------------------
@cache_page(60 * 60 * 15) # 1 hour cache
@user_owns_character()
def details(request, characterID):
    request.user
    
    
    try:
        member = getMember(int(characterID))
        
        if member.corped:
            member.date = getScanDate(Member.__name__)
        else:
            d = MemberDiff.objects.filter(characterID=member.characterID, new=False).order_by("-id")[0]
            member.date = utils.print_time_min(d.date)
    except ObjectDoesNotExist:
        member = Member(characterID=int(characterID), name="???")
    
    data = { 'member' : member }
    return render_to_response("members/member_details.html", data, context_instance=RequestContext(request))


#------------------------------------------------------------------------------
@cache_page(60 * 60 * 15) # 1 hour cache
@user_owns_character()
def access_changes_member_data(request, characterID):
    iDisplayStart = int(request.GET["iDisplayStart"])
    iDisplayLength = int(request.GET["iDisplayLength"])
    sEcho = int(request.GET["sEcho"])

    count, changes = getMemberAccessChanges(characterID=int(characterID),
                                            first_id=iDisplayStart, 
                                            last_id=iDisplayStart + iDisplayLength - 1)
    json_data = {
        "sEcho" : sEcho,
        "iTotalRecords" : count,
        "iTotalDisplayRecords" : count,
        "aaData" : changes
    }
    
    return HttpResponse(json.dumps(json_data))



#------------------------------------------------------------------------------
def getMember(id):
    colorThresholds = ColorThreshold.objects.all().order_by("threshold")
    member = Member.objects.get(characterID=id)
    member.corpDate = print_time_min(member.corpDate)
    member.lastLogin = print_time_min(member.lastLogin)
    member.lastLogoff = print_time_min(member.lastLogoff)
    member.base = resolveLocationName(member.baseID)
    member.color = get_access_color(member.accessLvl, colorThresholds)
    member.roles = member.getRoles(ignore_director=True)
    member.titles = member.getTitles()
    member.is_director = member.isDirector()
    
    return member




#------------------------------------------------------------------------------
def getMemberAccessChanges(characterID, first_id, last_id):
    
    roles = RoleMemberDiff.objects.filter(member=characterID).order_by("-id")
    titles = TitleMemberDiff.objects.filter(member=characterID).order_by("-id")
    
    count = roles.count() + titles.count()
    
    changes = utils.merge_lists(roles, titles, ascending=False, attribute="date")
    changes = changes[first_id:last_id]
    
    change_list = []
    for c in changes:
        try:
            access = '<a href="/titles/%d" class="title">%s</a>' % (c.title_id, unicode(c.title)) 
        except AttributeError:
            role_type_id = c.role.roleType.id
            role_id = c.role.roleID
            access = '<a href="/roles/%d/%d" class="role">%s</a>' % (role_type_id, role_id, unicode(c.role))
        
        change = [
            c.new,
            access,
            print_time_min(c.date)
        ] 

        change_list.append(change)
    
    return count, change_list
