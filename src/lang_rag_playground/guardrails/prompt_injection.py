import re

_PROMPT_INJECTION_RE = re.compile(
    r"""
    # 1. Talimatları geçersiz kılma
    \b(?:
        ignore|disregard|forget|override|bypass|neglect|
        ignorar|ignora|olvida|omitir|desconsiderar|
        ignorer|oublier|contourner|négliger|
        ignorieren|vergiss|umgehen|missachten|
        ignorare|dimentica|eludere|
        ignorar|esquecer|contornar|
        игнорировать|забудь|обойти|
        تجاهل|انسَ|تجاوز|
        忽略|忘记|无视|
        unut|yoksay|atla|geçersizleştir
    )\b.{0,80}\b(?:
        previous|prior|above|earlier|system|developer|
        instructions?|rules?|prompts?|directives?|
        anteriores?|instrucciones?|reglas?|indicaciones?|
        précédentes?|instructions?|règles?|
        vorherigen|anweisungen|regeln|
        precedenti|istruzioni|regole|
        anteriores|instruções|regras|
        предыдущие|инструкции|правила|
        السابقة|التعليمات|القواعد|
        之前的|指令|规则|
        önceki|talimatlar?|kurallar?|yönergeler?
    )\b

    # 2. Gizli prompt veya talimatları ifşa etme
    | \b(?:
        reveal|expose|show|print|display|repeat| disclose|
        reveal|mostrar|revelar|exponer|imprimir|
        dévoiler|révéler|afficher|répéter|
        enthülle|offenlegen|anzeigen|wiederhole|
        rivela|mostra|esponi|
        revelar|mostrar|expor|
        раскрой|покажи|выведи|
        اكشف|اعرض|أظهر|
        揭示|显示|输出|
        açıkla|göster|ifşa\s+et|yazdır|tekrarla
    )\b.{0,80}\b(?:
        system\s*prompt|developer\s*prompt|hidden\s+prompt|
        system\s+instructions?|internal\s+instructions?|
        secret\s+instructions?|confidential\s+prompt|
        prompt\s+system|instrucciones\s+del\s+sistema|
        instructions?\s+système|systemanweisungen|
        istruzioni\s+di\s+sistema|instruções\s+do\s+sistema|
        системн\w*\s+инструкц\w*|
        تعليمات\s+النظام|系统提示词|系统指令|
        sistem\s+prompt|gizli\s+talimatlar?|
        sistem\s+talimatlar?
    )\b

    # 3. Geliştirici modu ve jailbreak
    | \b(?:
        developer|dev|admin|god|sudo|unrestricted|
        geliştirici|yönetici|sınırsız
    )\s+mode\b
    | \b(?:dan\s+mode|jailbreak|jailbroken|脱狱)\b

    # 4. Rol veya kimlik değiştirme
    | \b(?:
        you\s+are\s+now|act\s+as|pretend\s+to\s+be|
        roleplay\s+as|switch\s+roles?|become|
        ahora\s+eres|actúa\s+como|
        tu\s+es\s+maintenant|agis\s+comme|
        du\s+bist\s+jetzt|tu\s+sei\s+ora|
        você\s+agora\s+é|ты\s+теперь|
        أنت\s+الآن|你现在是|
        sen\s+artık|rol\s+yap|gibi\s+davran|
        kimliğini\s+değiştir
    )\b

    # 5. Güvenlik mekanizmalarını kapatma
    | \b(?:
        disable|deactivate|remove|turn\s+off|circumvent|
        desactivar|deshabilitar|eliminar|
        désactiver|supprimer|désactiver|
        deaktivieren|ausschalten|entfernen|
        disattivare|rimuovere|
        desativar|remover|
        отключить|обойти|удалить|
        تعطيل|إزالة|
        禁用|关闭|移除|
        devre\s+dışı\s+bırak|kapat|kaldır|aş
    )\b.{0,80}\b(?:
        safety|security|guardrails?|filters?|restrictions?|
        policies|protections?|safeguards?|
        seguridad|protecciones|restricciones|
        sécurité|protections|restrictions|
        sicherheit|schutzmaßnahmen|beschränkungen|
        sicurezza|protezioni|restrizioni|
        segurança|proteções|restrições|
        безопасность|защиту|ограничения|
        الأمان|الحماية|القيود|
        安全机制|安全限制|防护措施|
        güvenlik|korumalar?|kısıtlamalar?|filtreler?
    )\b
    
    # 6. Gizli veya hassas bilgileri ifşa etme
    | \b(?:
        gizli|gizlilik|özel|hassas|mahrem|gizlenmiş|
        confidential|secret|hidden|private|sensitive|classified|
        secreto|confidencial|oculto|privado|sensible|
        secret|confidentiel|caché|privé|sensible|
        geheim|vertraulich|verborgen|privat|
        segreto|riservato|nascosto|
        sigiloso|confidencial|oculto|
        секретный|конфиденциальный|скрытый|
        سري|سرية|مخفي|
        机密|秘密|隐藏|隐私
    )\b.{0,60}\b(?:
        ver|veri|bilgi(?:leri)?|açıkla|ifşa\s+et|göster|
        paylaş|söyle|dök|çıkar|ilet|
        reveal|disclose|expose|show|provide|share|tell|print|dump|
        revelar|mostrar|exponer|proporcionar|compartir|
        révéler|divulguer|afficher|fournir|partager|
        enthüllen|offenlegen|anzeigen|bereitstellen|
        rivelare|mostrare|divulgare|fornire|
        revelar|expor|compartilhar|fornecer|
        раскрыть|покажи|предоставить|выведи|
        اكشف|اعرض|شارك|أظهر|
        揭示|显示|提供|泄露
    )\b
    | \b(?:
        ver|göster|açıkla|ifşa\s+et|paylaş|söyle|
        reveal|disclose|expose|provide|show|dump|
        revelar|révéler|offenlegen|rivelare|
        раскрыть|اكشف|揭示
    )\b.{0,60}\b(?:
        gizli\s+bilgiler?|gizli\s+veriler?|
        gizli\s+anahtarlar?|erişim\s+anahtarlar?|
        parolalar?|şifreler?|kimlik\s+bilgileri|
        confidential\s+information|secret\s+data|
        hidden\s+information|private\s+data|
        sensitive\s+information|classified\s+information|
        secrets?|credentials?|passwords?|API\s+keys?|
        access\s+tokens?|private\s+keys?|
        información\s+confidencial|datos\s+secretos|
        informations?\s+confidentielles|données\s+secrètes|
        vertrauliche\s+Informationen|geheime\s+Daten|
        informazioni\s+riservate|dati\s+segreti|
        informações\s+confidenciais|dados\s+secretos|
        конфиденциальные\s+данные|секретная\s+информация|
        المعلومات\s+السرية|البيانات\s+الحساسة|
        机密信息|秘密数据|敏感信息
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
