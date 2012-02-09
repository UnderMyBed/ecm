# Copyright (c) 2010-2012 Robin Jarry
# 
# This file is part of EVE Corporation Management.
# 
# EVE Corporation Management is free software: you can redistribute it and/or 
# modify it under the terms of the GNU General Public License as published by 
# the Free Software Foundation, either version 3 of the License, or (at your 
# option) any later version.
# 
# EVE Corporation Management is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY 
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for 
# more details.
# 
# You should have received a copy of the GNU General Public License along with 
# EVE Corporation Management. If not, see <http://www.gnu.org/licenses/>.

__date__ = "2010-02-03"
__author__ = "diabeteman"

try:
    import json
except ImportError:
    # fallback for python 2.5
    import django.utils.simplejson as json

from django.shortcuts import render_to_response
from django.template.context import RequestContext as Ctx

from ecm.core.eve import db
from ecm.core.eve import constants
from ecm.views.decorators import check_user_access
from ecm.apps.hr.models import Member
from ecm.apps.common.models import ColorThreshold, UserAPIKey


#------------------------------------------------------------------------------
@check_user_access()
def dashboard(request):
    data = {
        'unassociatedCharacters' : Member.objects.filter(corped=True, owner=None).count(),
        'playerCount' : Member.objects.filter(corped=True).exclude(owner=None).values("owner").distinct().count(),
        'memberCount' : Member.objects.filter(corped=True).count(),
        'accountsByPlayer' : avg_accounts_by_player(),
        'chraractersByPlayer' : avg_chraracters_by_player(),
        'positions' : positions_of_members(),
        'distribution' : access_lvl_distribution(),
        'directorAccessLvl' : Member.DIRECTOR_ACCESS_LVL 
    }
    
    return render_to_response("dashboard.html", data, Ctx(request))

#------------------------------------------------------------------------------
def avg_chraracters_by_player():
    players = Member.objects.filter(corped=True).exclude(owner=None).values("owner").distinct().count()
    characters = float(Member.objects.filter(corped=True).exclude(owner=None).count())
    if players:
        return characters / players
    else:
        return 0.0

#------------------------------------------------------------------------------
def avg_accounts_by_player():
    players = Member.objects.filter(corped=True).exclude(owner=None).values("owner").distinct().count()
    accounts = float(UserAPIKey.objects.all().count())
    if players:
        return accounts / players
    else:
        return 0.0

#------------------------------------------------------------------------------
def positions_of_members():
    positions = {"hisec" : 0, "lowsec" : 0, "nullsec" : 0}
    for m in Member.objects.filter(corped=True):
        solarSystemID = m.locationID
        if solarSystemID > constants.STATIONS_IDS:
            solarSystemID = db.getSolarSystemID(m.locationID)
        security = db.resolveLocationName(solarSystemID)[1]
        if security > 0.5:
            positions["hisec"] += 1
        elif security > 0:
            positions["lowsec"] += 1
        else:
            positions["nullsec"] += 1
    return json.dumps(positions)

#------------------------------------------------------------------------------
def access_lvl_distribution():
    thresholds = ColorThreshold.objects.all().order_by("threshold")
    for th in thresholds: 
        th.members = 0
    members = Member.objects.filter(corped=True).order_by("accessLvl")
    levels = members.values_list("accessLvl", flat=True)
    i = 0
    for level in levels:
        if level > thresholds[i].threshold:
            i += 1
        thresholds[i].members += 1
    
    distribution_json = []
    
    for th in thresholds:
        distribution_json.append({
            "threshold" : th.threshold,
            "members" : th.members,
            "color" : th.color
        })
    
    return json.dumps(distribution_json)