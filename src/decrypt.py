#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
import pandas as pd
import random
import string
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple


QUADGRAMS_PATH = "instructions/quadgrams_frequency.txt"
ENCODED_PATH   = "instructions/encoded_content.txt"
ALPHABET = string.ascii_uppercase
A2I = {c:i for i, c in enumerate(ALPHABET)}
I2A = {i:c for i, c in enumerate(ALPHABET)}

# ---------------------------
# Utilidades
# ---------------------------
def only_letters(text: str) -> str:
    """Mantém apenas letras A–Z, tudo maiúsculo."""
    return "".join(ch for ch in text.upper() if 'A' <= ch <= 'Z')

def apply_caesar(text: str, shift: int) -> str:
    """Aplica cifra de César com shift (decifra quando shift é negativo)."""
    return "".join(
        I2A[(A2I[ch] - shift) % 26] for ch in text if 'A' <= ch <= 'Z'
    )

def apply_substitution(cipher: str, key_map: Dict[str, str]) -> str:
    """Aplica substituição letra a letra usando o dicionário {CIPHER→PLAIN}."""
    return "".join(
        key_map.get(c, c) if 'A' <= c <= 'Z' else c
        for c in cipher
    )

def decode_binary_file(path: str) -> str:
    """Lê binários (em texto) e converte para caracteres ASCII."""
    with open(path, "r", encoding="utf-8") as f:
        tokens = f.read().split()

    chars = []
    for tok in tokens:
        try:
            code = int(tok, 2)
            # mantêm caracteres imprimíveis e quebra de linha
            if code == 10:
                chars.append('\n')
            elif 32 <= code <= 126 or code == 9:
                chars.append(chr(code))
        except ValueError:
            continue  # ignora tokens inválidos
    return "".join(chars)

def get_timestamp():
    return datetime.now().timestamp()

# ---------------------------
# Pontuação por Quad-grams
# ---------------------------
@dataclass
class QuadgramScorer:
    log_probs: Dict[str, float]
    floor: float

    @classmethod
    def from_file(cls, path: str) -> "QuadgramScorer":
        counts = {}
        total = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 2:
                    continue
                gram, cnt = parts[0].upper(), int(parts[1])
                if len(gram) == 4 and all('A' <= c <= 'Z' for c in gram):
                    counts[gram] = cnt
                    total += cnt
        # prob log10
        log_probs = {g: math.log10(c/total) for g, c in counts.items()}
        floor = math.log10(0.01/total)  # prob. muito pequena para grams ausentes
        return cls(log_probs, floor)

    def score(self, text: str) -> float:
        t = only_letters(text)
        if len(t) < 4:
            return -1e9
        s = 0.0
        for i in range(len(t)-3):
            g = t[i:i+4]
            s += self.log_probs.get(g, self.floor)
        return s

# ---------------------------
# Quebra por César (força bruta)
# ---------------------------
def break_caesar(cipher: str, scorer: QuadgramScorer, top_k: int = 5) -> List[Tuple[int, float, str]]:
    candidates = []
    for shift in range(1, 26):
        pt = apply_caesar(only_letters(cipher), shift)
        score = scorer.score(pt)
        candidates.append((shift, score, pt))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top_k]

# ---------------------------
# Quebra por Substituição (hill-climbing + restarts) — versão simples
# ---------------------------
def random_key() -> Dict[str, str]:
    """Gera uma chave aleatória (permuta o alfabeto). Mapeia CIPHER->PLAIN."""
    perm = list(ALPHABET)
    random.shuffle(perm)
    return {c: p for c, p in zip(ALPHABET, perm)}

def key_to_str(key_map: Dict[str, str]) -> str:
    """Converte o dicionário de chave para string de 26 letras (A..Z -> PLAIN)."""
    return "".join(key_map[c] for c in ALPHABET)

def str_to_key(s: str) -> Dict[str, str]:
    """Converte a string de 26 letras de volta para dicionário CIPHER->PLAIN."""
    return {c: p for c, p in zip(ALPHABET, s)}

def decrypt_with_key(cipher: str, key_s: str) -> str:
    """Aplica a chave (string) ao texto cifrado e retorna apenas letras A..Z decifradas."""
    return apply_substitution(only_letters(cipher), str_to_key(key_s))

def tweak_key(key_s: str) -> str:
    """Gera um vizinho trocando duas letras do mapeamento (swap simples)."""
    i, j = random.sample(range(26), 2)
    lst = list(key_s)
    lst[i], lst[j] = lst[j], lst[i]
    return "".join(lst)

def frequency_seed_key(cipher: str) -> str:
    """Semente baseada em frequência: mapeia as letras mais comuns do CIPHER
    para a ordem típica do inglês (ETAOIN...). É um bom chute inicial."""
    ENG_FREQ = "ETAOINSHRDLCUMWFGYPBVKJXQZ"

    # ordena letras do cifrado por frequência
    cnt = Counter(ch for ch in only_letters(cipher))
    cipher_order = "".join([c for c, _ in cnt.most_common()]) + \
                   "".join(c for c in ALPHABET if c not in cnt)

    # constrói destino: posição i (A=0) é a letra PLAIN para a letra i do CIPHER
    dest = ['?'] * 26
    for i, c in enumerate(cipher_order[:26]):
        dest[A2I[c]] = ENG_FREQ[i]

    # completa eventuais buracos (se houver)
    rest = [c for c in ALPHABET if c not in dest]
    for i in range(26):
        if dest[i] == '?':
            dest[i] = rest.pop()

    return "".join(dest)

def hill_climb_substitution(
    cipher: str,
    scorer: QuadgramScorer,
    max_iters: int = 4000,
    restarts: int = 30,
    patience: int = 800
) -> Tuple[str, float]:
    """Quebra substituição monoalfabética por hill-climbing com vários restarts.
    - Começa de chaves semente (frequência + aleatórias)
    - Faz swaps de duas letras; aceita se o score (quad-grams) melhora
    - Se não melhora por 'patience' passos, reinicia
    Retorna (melhor_plaintext, melhor_score)."""

    best_text, best_score = "", -1e100

    # sementes: 1 por frequência + algumas aleatórias
    seeds: List[str] = [frequency_seed_key(cipher)]
    for _ in range(max(1, restarts // 3)):
        seeds.append(key_to_str(random_key()))
    
    infos = []
    initial_timestamp = get_timestamp()

    for i in range(restarts):
        key_s = random.choice(seeds)

        plain = decrypt_with_key(cipher, key_s)
        score = scorer.score(plain)
        infos.append(("initial", score, score, i, None, get_timestamp()))

        no_gain = 0
        for j in range(max_iters):
            cand_key = tweak_key(key_s)
            cand_plain = decrypt_with_key(cipher, cand_key)
            cand_score = scorer.score(cand_plain)

            if cand_score > score:
                key_s, plain, score = cand_key, cand_plain, cand_score
                infos.append(("good candidate", cand_score, score, i, j, get_timestamp()))
                no_gain = 0
            else:
                no_gain += 1
                if no_gain >= patience:  # estagnou -> parte para outro restart
                    infos.append(("restarting", cand_score, score, i, j, get_timestamp()))
                    break
                else:
                    infos.append(("bad candidate", cand_score, score, i, j, get_timestamp()))

        if score > best_score:
            best_text, best_score = plain, score
            infos.append(("really good candidate", score, score, i, j, get_timestamp()))
    
    df = pd.DataFrame(
        infos, 
        columns=["type", "this_iteration_score", "best_score_so_far", "i", "j", "timestamp"]
    )
    df["elapsed_time"] = df["timestamp"] - initial_timestamp

    filename = f"scores_{round(initial_timestamp)}.csv"
    df.to_csv(
        filename, 
        index=False,
    )
    print(f"Dados de scores salvos em '{filename}'")
    
    return best_text, best_score

## Heurística de decisão e main
# ---------------------------
# Heurística de decisão e main
# ---------------------------
def likely_caesar_gain(score_caesar: float, score_sub: float, margem: float = 10.0) -> bool:
    """Decide por César se o melhor score de César não estiver muito pior que o de Substituição.
    'margem' é um colchão empírico (em log10). Quanto menor, mais exigente."""
    return score_caesar > (score_sub - margem)

def chunk_text(t: str, width: int = 80) -> str:
    """Quebra o texto em linhas legíveis no terminal."""
    return "\n".join(t[i:i+width] for i in range(0, len(t), width))

def main():
    # 1) Carrega os quad-grams (tabela de frequências p/ pontuar “quão inglês” é um texto)
    print("[1/4] Carregando quad-grams…")
    scorer = QuadgramScorer.from_file(QUADGRAMS_PATH)

    # 2) Lê o arquivo binário e converte para ASCII (ainda cifrado)
    print("[2/4] Lendo e decodificando binário…")
    raw = decode_binary_file(ENCODED_PATH)
    print("Prévia (120 chars):", raw[:120].replace("\n", "\\n"))

    # Só letras A–Z (remove pontuação/espaços p/ pontuar por quad-grams)
    cipher_only = only_letters(raw)
    print(f"Tamanho (A–Z): {len(cipher_only)}")

    # 3) Teste rápido de César (força bruta nos 25 shifts)
    print("\n[3/4] Tentando César…")
    top = break_caesar(raw, scorer, top_k=5)

    # mostra as 5 melhores tentativas com preview
    for rank, (shift, score, pt) in enumerate(top, 1):
        preview = pt[:70]
        print(f" {rank:>2}. shift={shift:2d} | score={score:10.2f} | {preview}…")

    caesar_best_shift, caesar_best_score, caesar_best_text = top[0]
    print(f"\nMelhor César: shift={caesar_best_shift} | score={caesar_best_score:.2f}")

    # 4) Substituição (hill-climbing com restarts). Parâmetros modestos e legíveis.
    print("\n[4/4] Tentando Substituição (hill-climb + restarts)…")
    sub_text, sub_score = hill_climb_substitution(
        raw, scorer,
        max_iters=1000,   # iterações por restart
        restarts=5,      # quantos recomeços
        patience=200      # para quando não melhora
    )
    print(f"Melhor Substituição: score={sub_score:.2f}")
    print("Preview:", sub_text[:70], "…")

    # Decisão final: escolhe o método com melhor score (com margem)
    print("\n>>> Resultado escolhido:")
    if likely_caesar_gain(caesar_best_score, sub_score, margem=10.0):
        print("CÉSAR")
        print(f"Shift = {caesar_best_shift}\n")
        print(chunk_text(caesar_best_text))
    else:
        print("SUBSTITUIÇÃO\n")
        print(chunk_text(sub_text))

if __name__ == "__main__":
    random.seed(42)  # reprodutibilidade básica
    main()
