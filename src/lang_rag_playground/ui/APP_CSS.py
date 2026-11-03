APP_CSS = """
#welcome-screen {
    max-width: 520px;
    margin: auto;
    justify-content: center;
    min-height: 80vh;
}
#welcome-title {
    text-align: center;
}
#graph-diagram .nodeLabel,
#graph-diagram .nodeLabel * {
    color: #111827 !important;
}
#graph-diagram .node text {
    fill: #111827 !important;
}
#thread-list .wrap {
    flex-direction: column;
    flex-wrap: nowrap;
    gap: 2px;
}
#thread-list label {
    width: 100%;
    padding: 8px 10px;
    border: none;
    border-radius: 8px;
    background: transparent;
    box-shadow: none;
    transform: none;
    font-weight: normal;
}
#thread-list label span {
    margin-left: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
#thread-list label:hover {
    background: var(--background-fill-secondary);
}
#thread-list label.selected {
    background: var(--border-color-primary);
    color: var(--body-text-color);
}
#thread-list input[type="radio"] {
    display: none;
}
"""