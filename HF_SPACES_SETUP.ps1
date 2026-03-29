# Quick setup for HF Spaces deployment (Windows PowerShell)

Write-Host "🚀 Setting up Visionex for Hugging Face Spaces deployment..." -ForegroundColor Cyan
Write-Host ""

# Initialize git if not already done
if (!(Test-Path .git)) {
    Write-Host "📦 Initializing git repository..." -ForegroundColor Yellow
    git init
    git add .
    git commit -m "Initial commit for HF Spaces deployment"
} else {
    Write-Host "✓ Git repository already initialized" -ForegroundColor Green
}

Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Create a GitHub repository: https://github.com/new"
Write-Host ""
Write-Host "2. Push this code:" -ForegroundColor Yellow
Write-Host '   git remote add origin https://github.com/YOUR_USERNAME/visionex-backend.git'
Write-Host '   git branch -M main'
Write-Host '   git push -u origin main'
Write-Host ""
Write-Host "3. Go to Hugging Face Spaces: https://huggingface.co/spaces" -ForegroundColor Cyan
Write-Host "4. Click 'Create New Space'"
Write-Host "5. Set SDK to 'Docker'"
Write-Host "6. Connect your GitHub repo"
Write-Host ""
Write-Host "7. Add these secrets in 'Repository secrets':" -ForegroundColor Yellow
Write-Host "   - MONGODB_URI"
Write-Host "   - GROQ_API_KEY"
Write-Host "   - GEMINI_API_KEY"
Write-Host "   - HF_MODEL_ID"
Write-Host "   - CORS_ORIGIN (e.g., https://your-frontend.vercel.app)"
Write-Host ""
Write-Host "8. Done! Space will auto-deploy and your API will be live 🎉" -ForegroundColor Green
Write-Host ""
Write-Host "📖 For more details, see: HF_SPACES_DEPLOY.md" -ForegroundColor Cyan
