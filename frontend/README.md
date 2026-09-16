# FIPE AI — Frontend

Interface web do agente FIPE AI (Next.js + TypeScript + Tailwind CSS).

Documentação completa do projeto (arquitetura, setup do backend, do notebook e deste frontend): veja o [README na raiz do repositório](../README.md#13-como-executar-o-frontend-nextjs).

Resumo rápido:

```bash
npm install
cp .env.example .env.local
npm run dev
```

Acesse `http://localhost:3000`. O frontend nunca acessa o Gemini ou a FIPE diretamente — todas as requisições passam pelo backend FastAPI (`NEXT_PUBLIC_API_BASE_URL`, padrão `http://localhost:8000`).
