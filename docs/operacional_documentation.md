# Operacional - Documentação do Aplicativo

Versão: 1.0  
Data: {{DATA_ATUAL}}  
Módulo: Operacional (Django)

## Sumário
1. Visão Geral
2. Navegação e Menus
3. Páginas e Funcionalidades
4. Regras de Negócio Específicas
5. Endpoints (URLs) e Ações
6. Permissões
7. Campos e Modelos Relevantes
8. Integrações e Fluxos entre Páginas
9. Instruções de Exportação para PDF
10. Anexos (Glossário)

---

## 1. Visão Geral
O módulo Operacional consolida rotinas de:
- Serviços e Movimentações por placa e período, com cálculo de valores a cobrar;
- Gestão de Contas a Receber (CR) e Contas a Pagar (CP);
- Geração de CR/CP a partir de movimentos e carta-frete;
- Gestão de Fechamentos diários por placa (conciliação de CP, CR e Lançamentos);
- Gestão de Lançamentos (receitas e despesas, com período e parcelas);
- Gestão de Abastecimento (litros, km e km/l).

Tecnologias principais: Django, Django Templates, Bootstrap, JS Fetch/AJAX.

---

## 2. Navegação e Menus
Menu lateral (Operacional):
- Serviços (Movimentações);
- Lançamentos;
- Contas a Receber;
- Contas a Pagar;
- Carta Frete;
- Fechamento (Gestão);
- Abastecimento.

Observação: “Abastecimento” encontra-se no mesmo nível hierárquico de “Movimentos”.

---

## 3. Páginas e Funcionalidades
### 3.1 Serviços / Movimentações (`operacional/servicos_movimentos.html`)
- Filtros por placa, agregado e período;
- Agrupamento por Placa → Tipo → Itens;
- Colunas: Data, OS, Cód./Item, Quantidade, Valor, Total, Percentual/Valor do Sistema (prioridade: vl_sistema > percentual), Cobrar;
- Regras de cálculo:
  - Serviço: cobra valor do serviço (não aplica percentual por padrão);
  - Outros: se `vl_sistema > 0`, cobrar = `vl_sistema * quantidade`; senão cobrar = `total + (percentual * total)`;
- Ações para gerar CR a partir de itens selecionados (com período e parcelas).

### 3.2 Contas a Receber (`operacional/contas_a_receber.html`)
- Filtros por placa e período;
- Tabela de cabeçalhos (placa, data, valor, qtd. itens e vencimentos);
- Modais para visualizar Itens e Vencimentos;
- Exclusão de item recalcula cabeçalho e atualiza a linha na tabela principal;
- Exclusão de cabeçalho bloqueada se houver vencimentos vinculados a fechamento.

### 3.3 Contas a Pagar (`operacional/contas_a_pagar.html`)
- Filtros por placa e período;
- Tabela de cabeçalhos (placa, data, valor, qtd. itens e vencimentos);
- Exclusão de item com recálculo; se último item, cabeçalho é excluído e linha removida da página.

### 3.4 Carta Frete (`operacional/carta_frete.html`)
- Filtros: placa, data início/fim e status aberto/fechado (com detecção por campo “situação” da view);
- Tabela por placa com totais (Valor, Adiantamento, Outros, Saldo) e Status agregado;
- Modal de Itens da carta frete com seleção e geração de CP (data de fechamento, parcelas/período). 

### 3.5 Fechamentos (lista) (`operacional/fechamentos.html`)
- Filtros (cod_ag, agregado, placa e data de fechamento);
- Tabela de Fechamentos com ações: itens, simulação de vencimentos, alterar data, excluir;
- Tabela de itens inclui edição de período/parcela.

### 3.6 Gestão de Fechamento (`operacional/gestao_fechamento.html`)
- Filtro obrigatório por data de fechamento (e opcional por placa);
- Consolidação por placa na data:
  - Total a Receber (somatório de vencimentos CR, fallback cabeçalho quando não houver vencimentos);
  - Total a Pagar (somatório de vencimentos CP, fallback cabeçalho quando não houver vencimentos);
  - Lançamentos (somados com sinal pela natureza: Receitas +, Despesas −);
  - Total final = CP − CR + Lançamentos;
- Ações por placa: “Detalhes”, “Criar/Vincular Fechamento”, “Enviar para AG” (habilitado se `fechamento_id` existir), “Excluir Fechamento”;
- Enviar AG preenche `cod_ag` (bloqueia alterações posteriores).

### 3.7 Lançamentos (`operacional/lancamentos.html`)
- Filtros: veículo/agregado, categoria, período, data início/fim, usuário;
- Cards de totais; tabela com natureza, período e parcela; modais para criar/editar/excluir.

### 3.8 Abastecimento (`operacional/abastecimento.html`)
- Filtros: placa, período, tipo de combustível;
- Indicadores: total de registros, veículos, total km, total litros, média km/l e total gasto;
- Tabela com: Data, Ponto de apoio, Combustível, Total KM, Litros, KM/L, Valor Litro, Valor Abastecimento;
- Edição inline de litros com botão “Salvar Todas” (batelada).

---

## 4. Regras de Negócio Específicas
- Serviços vs Não-serviços (Movimentações): prioridade de `vl_sistema` sobre `percentual` no cálculo de “Cobrar”;
- CR/CP: exclusão de itens e recálculo imediato; exclusão de cabeçalho condicionada a ausência de vencimentos com fechamento vinculado;
- Gestão de Fechamento: total final por placa = Contas a Pagar − Contas a Receber + Lançamentos(±).

---

## 5. Endpoints (URLs) e Ações
- Serviços Movimentos: `operacional:servicos_movimentos`
- CR:
  - Lista: `operacional:contas_a_receber`
  - Itens: `/operacional/contas-a-receber/<cr_id>/itens/`
  - Vencimentos: `/operacional/contas-a-receber/<cr_id>/vencimentos/`
  - Excluir item: `/operacional/contas-a-receber/itens/<item_id>/excluir/`
  - Excluir cabeçalho: `/operacional/contas-a-receber/<cr_id>/excluir/`
- CP:
  - Lista: `operacional:contas_a_pagar`
  - Itens: `/operacional/contas-a-pagar/<cap_id>/itens/`
  - Vencimentos: `/operacional/contas-a-pagar/<cap_id>/vencimentos/`
  - Excluir item: `/operacional/contas-a-pagar/itens/<item_id>/excluir/`
  - Excluir cabeçalho: `/operacional/contas-a-pagar/<cap_id>/excluir/`
- Carta Frete (API modal): `/operacional/servicos-movimentos/carta-frete/` e `/operacional/carta-frete/gerar/`
- Gestão de Fechamento:
  - Página: `operacional:gestao_fechamento`
  - Detalhes: `/operacional/gestao-fechamento/detalhes/`
  - Criar: `/operacional/gestao-fechamento/criar/`
  - Excluir: `/operacional/gestao-fechamento/excluir/`
  - Enviar AG: `/operacional/gestao-fechamento/enviar-ag/`
- Abastecimento:
  - Página: `operacional:abastecimento`
  - Salvar litros: `operacional:save_abastecimento_litros`

---

## 6. Permissões
Todas as páginas do Operacional exigem a permissão `operacional.acessar_operacional`.  
Ações de edição e exclusão também respeitam bloqueios de negócio (ex.: `cod_ag` no fechamento).

---

## 7. Campos e Modelos Relevantes
- Item: `percentual`, `vl_sistema` (cálculo de cobrar em Movimentações);
- Abastecimento: `qt_litros`, `total_km` → cálculo de `km/l`;
- Contas a Receber/Pagar (cabeçalhos e itens), Vencimentos;
- Fechamento: `data_fechamento`, `cod_ag`, `valor_total`.

---

## 8. Integrações e Fluxos entre Páginas
1) Serviços → Geração de CR (seleção de itens, data de fechamento, período e parcelas).  
2) Carta Frete → Geração de CP (itens selecionados e parâmetros).  
3) Fechamentos (Gestão) → consolidação por placa na data, com possibilidade de enviar AG.

---

## 9. Instruções de Exportação para PDF
Opção A (navegador):
- Abra `docs/operacional_documentation.html` no navegador;
- Ctrl+P (Imprimir) → Seletor “Salvar como PDF”;
- Em Mais definições: Tamanho A4, Margens Padrão, Habilitar “Cabeçalhos e rodapés” (opcional), Habilitar “Gráficos de segundo plano”.

Opção B (wkhtmltopdf):
```
wkhtmltopdf --enable-local-file-access docs/operacional_documentation.html docs/operacional_documentation.pdf
```

---

## 10. Anexos (Glossário)
- CR: Contas a Receber;
- CP: Contas a Pagar;
- Fechamento: consolidação por placa na data;
- AG: Sistema/ambiente externo que recebe fechamento consolidado;
- Km/L: métrica de eficiência (quilômetros por litro). 


