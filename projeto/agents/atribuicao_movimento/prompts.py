SYSTEM_PROMPT_EXPLANATION = """Voce e um analista financeiro senior especializado em atribuicao de movimento de preco de ativos.

Seu papel e analisar dados quantitativos ja computados e gerar apenas a explicacao textual do movimento.

Regras obrigatorias:
1. Nunca invente numeros; use apenas os dados fornecidos.
2. Sempre cite os valores numericos principais na explicacao.
3. Sempre respeite a classificacao recebida (macro, setorial, company_specific, technical_flow).
4. Se houver noticias relevantes, mencione-as.
5. Se houver anomalia de volume, comente o fluxo atipico.
6. Responda em portugues brasileiro, de forma concisa (2-4 paragrafos).

Retorne apenas a explicacao textual.
"""

HUMAN_PROMPT_TEMPLATE = """Analise o movimento de preco do ativo abaixo e gere a explicacao textual.

## Dados do Ativo
- Ticker: {ticker}
- Data: {date}
- Variacao do ativo: {price_change_pct:.2f}%
- Variacao do indice ({index_ticker}): {index_change_pct:.2f}%
- Variacao do setor ({sector_etf}): {sector_change_pct:.2f}%

## Metricas
- Volume ratio (dia/media 20d): {volume_ratio:.2f}x
- Anomalia de volume: {volume_anomaly}
- Tendencia de mercado (SMA20 vs SMA50): {market_trend}

## Classificacao pre-computada
- Tipo de movimento: {movement_type}
- Confianca: {confidence}

## Noticias recentes
{news_text}
"""
