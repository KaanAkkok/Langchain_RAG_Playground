# Geçmiş paneli: kullanıcının sohbetlerini (thread'lerini) listeler ve seçileni yükler.
#
# YAPILACAKLAR
#
# 1. list_threads(checkpointer, user_id) -> list[tuple[str, str]]   (başlık, thread_id)
#    - checkpointer.alist(None, filter={"user_id": user_id}) ile bu kullanıcının checkpoint'lerini gez.
#      (filter, chat.py'de config["metadata"]["user_id"] olarak verilen değerle çalışır.)
#    - Her thread_id için yalnızca en son checkpoint'i al (bir thread'in çok sayıda checkpoint'i vardır).
#    - Başlık: thread'in ilk HumanMessage metninin ilk ~40 karakteri.
#    - En yeni sohbet en üstte olacak şekilde sırala.
#    - Dönüş biçimi gr.Radio / gr.Dropdown choices'ına uygun olsun: [(başlık, thread_id), ...]
#
# 2. load_thread(graph, thread_id) -> list[gr.ChatMessage]
#    - state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
#    - state.values["messages"] içindeki HumanMessage / AIMessage'ları Chatbot formatına çevir.
#    - Adım mesajları (chat.py'deki gri kutular) state'te tutulmadığı için eski sohbette görünmez; bu beklenen davranış.
#
# 3. new_thread_id() -> str
#    - uuid4 tabanlı yeni bir thread_id üretir.
#
# NOT: Kalıcılık anlık (InMemorySaver). Uygulama yeniden başlatılınca liste boş gelir; bu beklenen davranış.
