#from email.headerregistry import Group
#import logging
#from django.forms import FloatField
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .models import  Link, Acesso
from django.contrib.auth.models import User, Group
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

# from .tasks import executar_tarefa



@login_required
def indexLinks(request):
    groups = User.objects.filter(username=request.user).values('groups')
    acessos  = Acesso.objects.filter(group__in=groups).values_list('link', flat=True)
    links = Link.objects.filter(id__in=acessos).values("id","desc", "link")
    
    print(links)
    context = {
        'links': links
    }

    # groupsMenus = User.objects.filter(username=request.user).values('groups__name')
    # for result in groupsMenus:
    #     if result.get("groups__name") == "PORTAL-LINKS-SEGURANCADB":
    #         groupSegurancaBD = True
    #     if result.get("groups__name") == "PORTAL-LINKS-UTILIZADORES":
    #         groupUtilizadores = True
            
    return render(request, 'indexLinks.html', {'links':links })
    # return HttpResponse('Teste ok!!!')
# Create your views here.



@login_required
def painel(request, id):

    print(id)
    groups = User.objects.filter(username=request.user).values('groups')
    acessos  = Acesso.objects.filter(group__in=groups, link=id).values_list('link', flat=True)
    
    if acessos:
        links = Link.objects.filter(id__in=acessos).values()[0]
        return render(request, 'painelLinks.html', {'frame': links})
    else:
        return render(request, '403.html')
    # return HttpResponse('Teste ok!!!')
# Create your views here.

