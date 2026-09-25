def calcular_percentis(tempo):
    lista_ordenada = sorted(tempo)

    n = len(lista_ordenada)

    if n == 0:
        return None, None, None

    idx_p50 = int((n - 1) * 0.50)
    idx_p95 = int((n - 1) * 0.95)
    idx_p99 = int((n - 1) * 0.99)

    p50 = lista_ordenada[idx_p50]
    p95 = lista_ordenada[idx_p95]
    p99 = lista_ordenada[idx_p99]

    return p50, p95, p99
