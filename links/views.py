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
from .powerbiService import get_report_metadata, generate_embed_token, PowerBIError
from django.http import HttpResponseServerError
import os   

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

USE_RLS = os.getenv("PBI_USE_RLS", "False") == "True"

@login_required # garante login no seu portal
def powerbi_report_view(request):
    try:
    # 1) Metadados do report (embedUrl e id)
        meta = get_report_metadata()
        embed_url = meta.get("embedUrl")
        report_id = meta.get("id")

        print(meta)

        # 2) (Opcional) Effective Identity para RLS
        identities = None
        if USE_RLS:
            # Exemplo simples: usar o username do Django como valor de RLS
            identities = [{
            "username": request.user.username,
            "roles": [], # ou ["RoleName"] se usar papéis
            "datasets": [meta.get("datasetId")]
            }]

        # 3) Embed token
        token_resp = generate_embed_token(access_level="View", report_id=report_id, identities=identities)
        embed_token = token_resp.get("token")

        print(100*'*')
        print(token_resp)
        print(embed_token)
        print(100*'*')

        context = {
        "embed_token": embed_token,
        "embed_url": embed_url,
        "report_id": report_id,
        "user": request.user,
        }

        print(100*'*')
        print(context)
        print(100*'*')

        return render(request, "powerbi_report.html", context)

    except PowerBIError as e:
        return HttpResponseServerError(f"Erro Power BI: {e}")


@login_required
def refresh_token_view(request):
    """
    View para renovar o token do Power BI via AJAX.
    Retorna um novo embed token em formato JSON.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        # Obter metadados do relatório
        meta = get_report_metadata()
        report_id = meta.get("id")
        
        # Verificar se deve usar RLS
        identities = None
        if USE_RLS:
            identities = [{
                "username": request.user.username,
                "roles": [],
                "datasets": [meta.get("datasetId")]
            }]
        
        # Gerar novo embed token
        token_resp = generate_embed_token(
            access_level="View", 
            report_id=report_id, 
            identities=identities
        )
        
        new_token = token_resp.get("token")
        
        if not new_token:
            return JsonResponse({'error': 'Falha ao gerar novo token'}, status=500)
        
        return JsonResponse({
            'success': True,
            'token': new_token,
            'expires_at': token_resp.get('expiration', ''),
            'message': 'Token renovado com sucesso'
        })
        
    except PowerBIError as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro Power BI: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }, status=500)