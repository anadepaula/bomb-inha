def four_pairwise(iterable):
    # based on itertools.pairwise
    iterator = iter(iterable)

    a = next(iterator, None)
    b = next(iterator, None)
    c = next(iterator, None)

    for d in iterator:
        yield a, b, c, d
        a, b, c = b, c, d

def form_quadgrams(letters):
    quadgrams = list(four_pairwise(letters))
   
    assert len(quadgrams) == len(letters)-3

    return quadgrams