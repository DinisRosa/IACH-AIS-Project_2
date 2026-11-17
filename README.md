# LaTeX — snapshot seguro

Cópia de segurança das fontes LaTeX da proposta, reunidas em `LaTeX/` e
verificadas (compilação da versão PT).

- `LaTeX/proposta_pt.tex` — versão em português (com `123` e
  *human-on-the-loop* a vermelho).
- `LaTeX/proposta_pt.pdf` — PDF compilado da versão PT.
- `LaTeX/proposta_IAHC_DINIS_ROSA.pdf` — PDF enviado ao professor; **não
  alterar** (mantém `128` e *human-in-the-loop*).
- `LaTeX/references.bib` — bibliografia.
- `LaTeX/FormattingGuidelines-IJCAI-ECAI-26/` — template oficial IJCAI-ECAI.
- `LaTeX/enunciado_proposta_de_projeto.pdf` — enunciado da proposta.

## Compilar

A partir de `LaTeX/`:

```bash
cd LaTeX
pdflatex proposta_pt
bibtex proposta_pt
pdflatex proposta_pt
pdflatex proposta_pt
```

Os artefactos de compilação (`*.aux`, `*.bbl`, `*.blg`, `*.log`, `*.out`,
`*.toc`) são ignorados pelo Git. A documentação completa e o plano de trabalho
estão no branch `main`.
