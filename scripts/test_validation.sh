#!/bin/bash

# Script per testare la validazione OAS Checker
# Uso: ./test_validation.sh [FILE_PATH] [RULESET]
#   FILE_PATH: Path del file OpenAPI da validare (default: example_api.yml)
#   RULESET: Nome del ruleset da usare (default: spectral)
#   Rulesets disponibili: spectral, spectral-full, spectral-generic, spectral-modi, spectral-security

# Colori per output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurazione
API_URL="http://localhost:8000"
FILE_PATH="${1:-example_api.yml}"
RULESET="${2:-spectral}"
ERRORS_ONLY="false"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Validazione OAS Checker${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verifica che il file esista
if [ ! -f "$FILE_PATH" ]; then
    echo -e "${RED}❌ Errore: File $FILE_PATH non trovato${NC}"
    exit 1
fi

echo -e "${YELLOW}📄 File: $FILE_PATH${NC}"
echo -e "${YELLOW}📋 Ruleset: $RULESET${NC}"
echo -e "${YELLOW}🔍 Errors only: $ERRORS_ONLY${NC}"
echo ""

# Step 1: Verifica che il servizio sia attivo
echo -e "${BLUE}Step 1: Verifica servizio...${NC}"
if ! curl -s -f "$API_URL/status" > /dev/null; then
    echo -e "${RED}❌ Servizio non raggiungibile su $API_URL${NC}"
    echo -e "${YELLOW}💡 Avvia i container con: docker-compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Servizio attivo${NC}"
echo ""

# Step 2: Verifica rulesets disponibili
echo -e "${BLUE}Step 2: Verifica rulesets disponibili...${NC}"
RULESETS=$(curl -s "$API_URL/oas/rulesets" | python3 -c "import sys, json; print(', '.join(json.load(sys.stdin)['rulesets']))")
echo -e "${GREEN}✅ Rulesets disponibili: $RULESETS${NC}"
echo ""

# Step 3: Submit validazione
echo -e "${BLUE}Step 3: Invio file per validazione...${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/oas/validate" \
  -F "file=@$FILE_PATH" \
  -F "ruleset=$RULESET" \
  -F "errors_only=$ERRORS_ONLY")

VALIDATION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('validation_id', ''))")
STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")

if [ -z "$VALIDATION_ID" ]; then
    echo -e "${RED}❌ Errore durante l'invio:${NC}"
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi

echo -e "${GREEN}✅ Validazione creata${NC}"
echo -e "${YELLOW}   ID: $VALIDATION_ID${NC}"
echo -e "${YELLOW}   Status: $STATUS${NC}"
echo ""

# Step 4: Attendi completamento
echo -e "${BLUE}Step 4: Attendo completamento validazione...${NC}"
MAX_ATTEMPTS=30
ATTEMPT=0
COMPLETED=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep 2
    ATTEMPT=$((ATTEMPT + 1))

    REPORT=$(curl -s "$API_URL/oas/report/$VALIDATION_ID")
    CURRENT_STATUS=$(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")

    echo -ne "\r${YELLOW}   Tentativo $ATTEMPT/$MAX_ATTEMPTS - Status: $CURRENT_STATUS${NC}"

    if [ "$CURRENT_STATUS" = "COMPLETED" ] || [ "$CURRENT_STATUS" = "FAILED" ]; then
        COMPLETED=true
        break
    fi
done

echo ""
echo ""

if [ "$COMPLETED" = false ]; then
    echo -e "${RED}❌ Timeout: validazione non completata in tempo${NC}"
    exit 1
fi

# Step 5: Mostra report
echo -e "${BLUE}Step 5: Report validazione${NC}"
echo -e "${BLUE}========================================${NC}"

REPORT=$(curl -s "$API_URL/oas/report/$VALIDATION_ID")

# Salva il report completo in un file
REPORT_FILE="validation_report_${VALIDATION_ID}.json"
echo "$REPORT" | python3 -m json.tool > "$REPORT_FILE"
echo -e "${GREEN}✅ Report salvato in: $REPORT_FILE${NC}"
echo ""

# Estrai informazioni chiave
FINAL_STATUS=$(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
IS_VALID=$(echo "$REPORT" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('report', {}).get('valid', False))")
TOTAL_ISSUES=$(echo "$REPORT" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('report', {}).get('summary', {}).get('total_issues', 0))")
ERRORS=$(echo "$REPORT" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('report', {}).get('summary', {}).get('errors', 0))")
WARNINGS=$(echo "$REPORT" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('report', {}).get('summary', {}).get('warnings', 0))")
INFO=$(echo "$REPORT" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('report', {}).get('summary', {}).get('info', 0))")
CREATED_AT=$(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('created_at', ''))")
COMPLETED_AT=$(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('completed_at', ''))")
ERROR_MSG=$(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error', 'None'))")

# Mostra riepilogo
echo -e "${BLUE}📊 RIEPILOGO VALIDAZIONE${NC}"
echo -e "   Validation ID: ${YELLOW}$VALIDATION_ID${NC}"
echo -e "   Status: ${YELLOW}$FINAL_STATUS${NC}"
echo -e "   Valid: ${YELLOW}$IS_VALID${NC}"
echo -e "   Created: ${YELLOW}$CREATED_AT${NC}"
echo -e "   Completed: ${YELLOW}$COMPLETED_AT${NC}"
echo ""

echo -e "${BLUE}📈 STATISTICHE${NC}"
echo -e "   Total Issues: ${YELLOW}$TOTAL_ISSUES${NC}"
echo -e "   Errors: ${RED}$ERRORS${NC}"
echo -e "   Warnings: ${YELLOW}$WARNINGS${NC}"
echo -e "   Info: ${BLUE}$INFO${NC}"
echo ""

if [ "$ERROR_MSG" != "None" ]; then
    echo -e "${RED}⚠️  ERRORE: $ERROR_MSG${NC}"
    echo ""
fi

# Mostra dettagli errori se presenti
if [ "$ERRORS" != "0" ]; then
    echo -e "${RED}🔴 ERRORI RILEVATI:${NC}"
    echo "$REPORT" | python3 -c "
import sys, json
report = json.load(sys.stdin)
errors = report.get('report', {}).get('errors', [])
for i, err in enumerate(errors, 1):
    print(f'  {i}. {err.get(\"message\", \"\")}')
    print(f'     Path: {err.get(\"path\", \"\")}')
    print(f'     Rule: {err.get(\"code\", \"\")}')
    print()
"
fi

# Mostra dettagli warnings se presenti
if [ "$WARNINGS" != "0" ]; then
    echo -e "${YELLOW}⚠️  WARNINGS RILEVATI:${NC}"
    echo "$REPORT" | python3 -c "
import sys, json
report = json.load(sys.stdin)
warnings = report.get('report', {}).get('warnings', [])
for i, warn in enumerate(warnings, 1):
    print(f'  {i}. {warn.get(\"message\", \"\")}')
    print(f'     Path: {warn.get(\"path\", \"\")}')
    print(f'     Rule: {warn.get(\"code\", \"\")}')
    print()
"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Test completato!${NC}"
echo -e "${YELLOW}📁 Report completo salvato in: $REPORT_FILE${NC}"
echo ""
