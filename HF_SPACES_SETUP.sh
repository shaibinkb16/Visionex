#!/bin/bash
# Quick setup for HF Spaces deployment

echo "🚀 Setting up Visionex for Hugging Face Spaces deployment..."

# Initialize git if not already done
if [ ! -d .git ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for HF Spaces deployment"
else
    echo "✓ Git repository already initialized"
fi

echo ""
echo "📋 Next steps:"
echo "1. Create a GitHub repository (https://github.com/new)"
echo "2. Push this code:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/visionex-backend.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Go to Hugging Face Spaces: https://huggingface.co/spaces"
echo "4. Click 'Create New Space'"
echo "5. Set SDK to 'Docker'"
echo "6. Connect your GitHub repo"
echo "7. Add these secrets in 'Repository secrets':"
echo "   - MONGODB_URI"
echo "   - GROQ_API_KEY"
echo "   - GEMINI_API_KEY"
echo "   - HF_MODEL_ID"
echo "   - CORS_ORIGIN"
echo ""
echo "8. Done! Space will auto-deploy and your API will be live 🎉"
echo ""
echo "📖 For more details, see: HF_SPACES_DEPLOY.md"
