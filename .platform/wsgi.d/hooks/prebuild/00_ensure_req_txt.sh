#!/bin/bash
set -e
set -x

# Verifica se req.txt existe na raiz do diretório de staging
if [ -f "/var/app/staging/req.txt" ]; then
    echo "req.txt encontrado em /var/app/staging/"
else
    echo "req.txt NÃO encontrado em /var/app/staging/. Verificando subdiretórios..."
    # Procura por req.txt em subdiretórios comuns de artefatos aninhados
    find /var/app/staging/ -name req.txt -print -quit | while read -r found_path; do
        if [ -n "$found_path" ]; then
            echo "req.txt encontrado em: $found_path"
            # Copia para a raiz do staging para que cfn-init o encontre
            cp "$found_path" /var/app/staging/req.txt
            echo "req.txt copiado para /var/app/staging/"
            exit 0 # Sai do loop e do script
        fi
    done
    echo "ERRO CRÍTICO: req.txt não foi encontrado em nenhum lugar no pacote descompactado. Verifique o artefato do CodeBuild."
    exit 1 # Falha o deploy se não encontrar
fi

echo "--- Executando o diagnóstico de Python/pip ---"
which python3
python3 --version
which pip3
pip3 --version
echo "Conteúdo de req.txt (primeiras 5 linhas, após verificação/cópia):"
head -n 5 req.txt
echo "--- Fim do Diagnóstico ---"

# Comando original para instalar as dependências
echo "--- Instalando dependências com pip ---"
pip3 install -r req.txt >> /var/log/pip_install_full.log 2>&1 || { echo "ERRO: pip install falhou. Verifique /var/log/pip_install_full.log." >> /var/log/eb-engine.log; exit 1; }

echo "--- Instalação de dependências concluída ---"