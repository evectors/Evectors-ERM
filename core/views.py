# Create your views here.
from erm.core.models import *
from erm.lib.api import *
from django.shortcuts import render_to_response

def index(request):
    last_entities = Entity.objects.all().order_by('name')[:10]
    return render_to_response('core/index.html', {'last_entities': last_entities})

def xd_receiver(request):
    if request.facebook_message is not None:
        facebook_message = request.facebook_message
    else:
        facebook_message = ''
    return render_to_response('xdreceiver.html',{'facebook_message': facebook_message})

def test(request):
     return render_to_response('test.html')

def req_bounce(request, args):
    return HttpResponse("bounced: %s [%s]" % (request,args), 'text/plain')

#@valid_api
#@valid_method
#@parse_params
#def splitter(request, api_key, params, **kw):
#    return HttpResponse("%s [%s, %s, %s]" % (request, api_key, params, kw), 'text/plain')