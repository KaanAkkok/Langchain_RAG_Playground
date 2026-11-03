APP_JS = """
async () => {
    const loadMermaid = () => new Promise((resolve, reject) => {
        if (window.mermaid) {
            resolve(window.mermaid);
            return;
        }
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js";
        script.onload = () => resolve(window.mermaid);
        script.onerror = reject;
        document.head.appendChild(script);
    });

    try {
        const mermaid = await loadMermaid();
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });

        const renderGraphs = async () => {
            const nodes = [...document.querySelectorAll(".mermaid:not([data-rendered])")];
            if (!nodes.length) {
                return;
            }
            nodes.forEach((node) => node.setAttribute("data-rendered", "true"));
            await mermaid.run({ nodes });
        };

        const observer = new MutationObserver(() => renderGraphs());
        observer.observe(document.body, { childList: true, subtree: true });
        await renderGraphs();
    } catch (error) {
        console.error("Mermaid yüklenemedi veya grafik çizilemedi.", error);
    }
}
"""