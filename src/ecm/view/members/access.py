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

from django.views.decorators.cache import cache_page
from django.template.context import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponse

from ecm.view import getScanDate
from ecm.data.roles.models import TitleMembership, RoleMemberDiff, TitleMemberDiff
from ecm.core import utils
from ecm.core.utils import print_time_min
from ecm.core.auth import user_is_director



#------------------------------------------------------------------------------
@cache_page(60 * 60 * 15) # 1 hour cache
@user_is_director()
def access_changes(request):
    data = {
        'scan_date' : getScanDate(TitleMembership.__name__) 
    }
    return render_to_response("members/access_changes.html", data, context_instance=RequestContext(request))


#------------------------------------------------------------------------------
@cache_page(60 * 60 * 15) # 1 hour cache
@user_is_director()
def access_changes_data(request):
    iDisplayStart = int(request.GET["iDisplayStart"])
    iDisplayLength = int(request.GET["iDisplayLength"])
    sEcho = int(request.GET["sEcho"])

    count, changes = getAccessChanges(first_id=iDisplayStart, 
                                      last_id=iDisplayStart + iDisplayLength - 1)
    json_data = {
        "sEcho" : sEcho,
        "iTotalRecords" : count,
        "iTotalDisplayRecords" : count,
        "aaData" : changes
    }
    
    return HttpResponse(json.dumps(json_data))



#------------------------------------------------------------------------------
def getAccessChanges(first_id, last_id):
    
    roles = RoleMemberDiff.objects.all().order_by("-date")
    titles = TitleMemberDiff.objects.all().order_by("-date")
    
    count = roles.count() + titles.count()
    
    changes = utils.merge_lists(roles, titles, ascending=False, attribute="date")
    changes = changes[first_id:last_id]
    
    change_list = []
    for c in changes:
        try:
            access = '<a href="/titles/%d" class="title">%s</a>' % (c.title_id, unicode(c.title)) 
        except AttributeError:
            role_type = c.role.roleType.typeName
            role_id = c.role.roleID
            access = '<a href="/roles/%s/%d" class="role">%s</a>' % (role_type, role_id, unicode(c.role))
        
        try:
            member_url = '<a href="/members/%d">%s</a>' % (c.member.characterID, c.member.name)
        except:
            member_url = '<a href="/members/%d">%s</a>' % (c.member_id, "???")
        
        change = [
            c.new,
            member_url,
            access,
            print_time_min(c.date)
        ]

        change_list.append(change)
    
    return count, change_list