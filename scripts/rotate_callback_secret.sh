#!/bin/bash
# rotate_callback_secret.sh
# Script per rotazione manuale del CALLBACK_SECRET
#
# Uso:
#   ./scripts/rotate_callback_secret.sh
#
# Prerequisiti:
#   - Azure CLI installato e autenticato (az login)
#   - Permessi per accedere a Key Vault e gestire App Services
#
# Variabili da configurare:
#   VAULT_NAME: Nome del Key Vault
#   RESOURCE_GROUP: Nome del resource group
#   FUNCTION_NAME: Nome dell'Azure Function
#   ESERVICE_NAME: Nome dell'E-Service (Web App)

set -e

# Configuration - MODIFY THESE VALUES
VAULT_NAME="${VAULT_NAME:-your-oaschecker-vault}"
RESOURCE_GROUP="${RESOURCE_GROUP:-your-rg}"
FUNCTION_NAME="${FUNCTION_NAME:-your-function}"
ESERVICE_NAME="${ESERVICE_NAME:-your-eservice}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔄 Starting CALLBACK_SECRET rotation..."
echo ""
echo "Configuration:"
echo "  Key Vault: $VAULT_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Azure Function: $FUNCTION_NAME"
echo "  E-Service: $ESERVICE_NAME"
echo ""

# Check Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI not found. Please install it first.${NC}"
    echo "   https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo -e "${RED}❌ Not logged in to Azure. Run 'az login' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Azure CLI configured${NC}"
echo ""

# Step 1: Generate new secret
echo "1/6 Generating new secret..."
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
if [ -z "$NEW_SECRET" ]; then
    echo -e "${RED}❌ Failed to generate secret${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Secret generated (length: ${#NEW_SECRET})${NC}"
echo ""

# Step 2: Save to Key Vault
echo "2/6 Saving to Key Vault..."
if az keyvault secret set \
    --vault-name "$VAULT_NAME" \
    --name callback-secret \
    --value "$NEW_SECRET" \
    --output none 2>/dev/null; then
    echo -e "${GREEN}✅ Secret saved to Key Vault${NC}"
else
    echo -e "${RED}❌ Failed to save secret to Key Vault${NC}"
    echo "   Check that Key Vault '$VAULT_NAME' exists and you have permissions"
    exit 1
fi
echo ""

# Step 3: Update Azure Function
echo "3/6 Updating Azure Function..."
if az functionapp config appsettings set \
    --name "$FUNCTION_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings "CALLBACK_SECRET=@Microsoft.KeyVault(SecretUri=https://$VAULT_NAME.vault.azure.net/secrets/callback-secret)" \
    --output none 2>/dev/null; then
    echo -e "${GREEN}✅ Function updated${NC}"
else
    echo -e "${RED}❌ Failed to update Function${NC}"
    echo "   Check that Function '$FUNCTION_NAME' exists in resource group '$RESOURCE_GROUP'"
    exit 1
fi
echo ""

# Step 4: Update E-Service
echo "4/6 Updating E-Service..."
if az webapp config appsettings set \
    --name "$ESERVICE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings "CALLBACK_SECRET=@Microsoft.KeyVault(SecretUri=https://$VAULT_NAME.vault.azure.net/secrets/callback-secret)" \
    --output none 2>/dev/null; then
    echo -e "${GREEN}✅ E-Service updated${NC}"
else
    echo -e "${RED}❌ Failed to update E-Service${NC}"
    echo "   Check that Web App '$ESERVICE_NAME' exists in resource group '$RESOURCE_GROUP'"
    exit 1
fi
echo ""

# Step 5: Restart services
echo "5/6 Restarting services..."
echo "   This may take 30-60 seconds..."

# Restart in parallel
az functionapp restart --name "$FUNCTION_NAME" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null &
FUNC_PID=$!

az webapp restart --name "$ESERVICE_NAME" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null &
WEBAPP_PID=$!

# Wait for both
wait $FUNC_PID
FUNC_EXIT=$?

wait $WEBAPP_PID
WEBAPP_EXIT=$?

if [ $FUNC_EXIT -eq 0 ] && [ $WEBAPP_EXIT -eq 0 ]; then
    echo -e "${GREEN}✅ Services restarted${NC}"
else
    echo -e "${YELLOW}⚠️  Some services may not have restarted properly${NC}"
fi
echo ""

# Step 6: Verify
echo "6/6 Verifying rotation..."
echo "   Waiting 30 seconds for services to be ready..."
sleep 30

ESERVICE_URL="https://$ESERVICE_NAME.azurewebsites.net"
if curl -s -f "$ESERVICE_URL/status" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ E-Service is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  E-Service health check failed (may still be starting)${NC}"
    echo "   Manually verify at: $ESERVICE_URL/status"
fi
echo ""

echo -e "${GREEN}✅ Secret rotation completed successfully!${NC}"
echo ""
echo "📝 Next rotation due: $(date -v +90d '+%Y-%m-%d' 2>/dev/null || date -d '+90 days' '+%Y-%m-%d' 2>/dev/null || echo 'in 90 days')"
echo ""
echo "🔒 Old secret versions are retained in Key Vault for rollback if needed."
echo "   View versions: az keyvault secret list-versions --vault-name $VAULT_NAME --name callback-secret"
