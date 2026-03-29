# 🎬 TMDB Movie Search for Ulauncher

Uma extensão de alto desempenho para o Ulauncher que permite navegar, pesquisar e descobrir filmes usando a API do The Movie Database (TMDB).

## ✨ Recursos

- **Pesquisa Instantânea**: Encontre qualquer filme enquanto você digita.
- **Filmes em Alta**: Veja o que está em alta hoje acionando a extensão sem nenhuma consulta.
- **Sugestões Inteligentes**: Receba recomendações aleatórias ou filtre por gênero.
- **Informações Detalhadas**: Veja avaliações (⭐), duração, gêneros, elenco e diretor.
- **Disponibilidade em Streaming**: Verifique onde assistir (Flatrate) de acordo com a sua região.
- **Desempenho Otimizado**: Usa pool de workers para processamento de imagens e buscas em segundo plano, mantendo a interface fluida.
- **Suporte Offline**: Acesse resultados previamente armazenados em cache mesmo sem internet.

## 🚀 Instalação

1. Abra as Preferências do Ulauncher.
2. Vá em **Extensions > Add extension**.
3. Cole a URL do repositório:  
   `https://github.com/your-username/ulauncher-tmdb`

## 🔑 Configuração

Para usar esta extensão, você precisa fornecer sua própria chave da API do TMDB:

1. Crie uma conta em [TheMovieDB.org](https://www.themoviedb.org/).
2. Vá em **Settings > API**.
3. Gere uma chave de API pessoal (v3 auth).
4. Nas configurações da extensão no Ulauncher, cole sua chave no campo **TMDB API Key**.

## 🛠️ Como Usar

| Comando              | Ação |
|----------------------|------|
| `m <consulta>`       | Pesquisar um filme específico |
| `m` (sem consulta)   | Mostrar filmes em alta no momento |
| `sugest random`      | Sugerir um filme completamente aleatório (duração mínima de 70 minutos) |
| `sugest <gênero>`    | Sugerir um filme de um gênero específico (ex: `sugest drama`, `sugest horror`) |

**Gêneros suportados:** Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Science Fiction, Romance, Thriller e Horror.

## ⚙️ Detalhes Técnicos

- **Debounce**: 0.1s para otimizar chamadas à API.
- **Processamento de Imagens**: Baixa posters, redimensiona para 120x180 e aplica cantos arredondados.
- **Confiança nos Dados**: Escapamento profundo de HTML para evitar artefatos como `&amp;`.
- **Cache**: Armazena detalhes de filmes e posters localmente para maior velocidade e menor uso de dados.

## 👤 Créditos

- **Desenvolvedor**: Xavier
- **Provedor de Dados**: The Movie Database (TMDB)

---

**Quer que eu adicione uma seção sobre como personalizar as palavras-chave de ativação padrão?**
