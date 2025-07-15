import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def apply_mitigation_strategy(risk_factors: list, current_action: str) -> str:
    """Aplica estratégias de mitigação com base nos fatores de risco identificados."""
    logger.info(f"Aplicando estratégias de mitigação para ação: {current_action} com riscos: {risk_factors}")

    if "Baixa liquidez" in risk_factors:
        logger.warning("Risco de baixa liquidez detectado. Reduzindo o tamanho da posição.")
        return "reduce_position_size"
    
    if "Preço muito volátil" in risk_factors:
        logger.warning("Risco de alta volatilidade de preço detectado. Aumentando o slippage tolerance e monitorando.")
        return "increase_slippage_tolerance"

    if "Nome genérico pode indicar falta de originalidade" in risk_factors:
        logger.warning("Risco de token genérico. Reavaliando o interesse da comunidade e a legitimidade.")
        return "reassess_community_interest"

    if "Detectado muito tarde pós-migração" in risk_factors:
        logger.warning("Risco de detecção tardia. Reavaliando o potencial de crescimento.")
        return "reassess_growth_potential"

    logger.info("Nenhuma estratégia de mitigação específica aplicada para os riscos atuais.")
    return "no_change"


# Para teste local
if __name__ == "__main__":
    print("\n--- Teste de estratégias de mitigação ---")

    # Cenário 1: Baixa liquidez
    risks_1 = ["Baixa liquidez", "Preço estável"]
    action_1 = "BUY"
    result_1 = apply_mitigation_strategy(risks_1, action_1)
    print(f"Cenário 1: {result_1}")

    # Cenário 2: Alta volatilidade
    risks_2 = ["Preço muito volátil", "Alto volume total"]
    action_2 = "STRONG_BUY"
    result_2 = apply_mitigation_strategy(risks_2, action_2)
    print(f"Cenário 2: {result_2}")

    # Cenário 3: Múltiplos riscos
    risks_3 = ["Baixa liquidez", "Detectado muito tarde pós-migração", "Nome genérico pode indicar falta de originalidade"]
    action_3 = "CONSIDER"
    result_3 = apply_mitigation_strategy(risks_3, action_3)
    print(f"Cenário 3: {result_3}")

    # Cenário 4: Nenhum risco específico
    risks_4 = ["Preço estável", "Alto interesse no Twitter"]
    action_4 = "BUY"
    result_4 = apply_mitigation_strategy(risks_4, action_4)
    print(f"Cenário 4: {result_4}")










