import os
import json
import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import redis
from redis.exceptions import RedisError
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# ==========================================
# 1. FUNÇÕES DO MONGODB
# ==========================================
def conectar_mongodb():
    """Conecta ao MongoDB Atlas e retorna a referência do banco 'desafio_nosql'."""
    uri = os.getenv("MONGO_URI")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping') # Testa a conexão
        print("✅ MongoDB conectado com sucesso!")
        return client["desafio_nosql"]
    except ConnectionFailure as e:
        print(f"❌ Erro ao conectar no MongoDB: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado no MongoDB: {e}")
        return None

def popular_mongodb(db):
    """Insere dados iniciais no MongoDB."""
    db.produtos.delete_many({}) # Limpa a coleção para não duplicar nos testes
    produtos = [
        {"nome": "Notebook", "preco": 3500.00, "categoria": "Eletrônicos"},
        {"nome": "Mouse", "preco": 80.00, "categoria": "Eletrônicos"},
        {"nome": "Caderno", "preco": 8.00, "categoria": "Papelaria"}
    ]
    db.produtos.insert_many(produtos)
    print("-> 3 produtos inseridos no MongoDB.")

def consultar_preco_maior_10(db):
    """Retorna produtos com preço > 10."""
    return list(db.produtos.find({"preco": {"$gt": 10}}, {"_id": 0}))

def atualizar_preco(db, nome_produto, novo_preco):
    """Atualiza o preço de um produto específico."""
    db.produtos.update_one({"nome": nome_produto}, {"$set": {"preco": novo_preco}})
    print(f"-> Preço do {nome_produto} atualizado para {novo_preco}.")

def remover_por_categoria(db, categoria):
    """Remove um produto pela categoria."""
    resultado = db.produtos.delete_many({"categoria": categoria})
    print(f"-> {resultado.deleted_count} produto(s) da categoria '{categoria}' removido(s).")


# ==========================================
# 2. FUNÇÕES DO REDIS
# ==========================================
def conectar_redis():
    """Conecta ao Redis Cloud e retorna a instância."""
    host = os.getenv("REDIS_HOST")
    port = os.getenv("REDIS_PORT")
    password = os.getenv("REDIS_PASSWORD")
    try:
        r = redis.Redis(host=host, port=port, password=password, decode_responses=True)
        r.ping() # Testa a conexão
        print("✅ Redis conectado com sucesso!")
        return r
    except RedisError as e:
        print(f"❌ Erro ao conectar no Redis: {e}")
        return None

def operacoes_basicas_redis(r):
    """Realiza as operações básicas exigidas no Redis."""
    # String
    r.set("mensagem:inicio", "Bem-vindo ao sistema com MongoDB e Redis!")
    print(f"-> Mensagem do Redis: {r.get('mensagem:inicio')}")
    
    # Hash
    r.hset("usuario:1", mapping={"nome": "João Silva", "email": "joao@email.com"})
    print(f"-> Usuário salvo no Hash Redis: {r.hgetall('usuario:1')}")
    
    # Lista
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    r.rpush("logs:acesso", f"{timestamp} - Login realizado")
    r.rpush("logs:acesso", f"{timestamp} - Consulta na base de dados")
    
    # Exibir Lista
    logs = r.lrange("logs:acesso", 0, -1)
    print("-> Logs de acesso (Lista Redis):")
    for log in logs:
        print(f"   {log}")


# ==========================================
# 3. CASO INTEGRADO (CACHE COM REDIS)
# ==========================================
def buscar_produto_com_cache(db, r, nome_produto):
    """Busca o produto no Redis; se não achar, busca no Mongo e salva no Redis."""
    chave_redis = f"produto:{nome_produto}"
    
    # 1. Verifica no Redis
    produto_cache = r.get(chave_redis)
    if produto_cache:
        print(f"\n⚡ PRODUTO '{nome_produto}' ENCONTRADO NO CACHE (REDIS):")
        return json.loads(produto_cache)
    
    # 2. Caso não exista no Redis, busca no MongoDB
    print(f"\n⏳ Produto '{nome_produto}' não está no cache. Buscando no MONGODB...")
    produto_mongo = db.produtos.find_one({"nome": nome_produto}, {"_id": 0})
    
    # 3. Salva no Redis com TTL de 60 segundos
    if produto_mongo:
        r.setex(chave_redis, 60, json.dumps(produto_mongo))
        print(f"💾 Produto '{nome_produto}' salvo no cache do Redis (TTL: 60s).")
        return produto_mongo
    else:
        print("❌ Produto não encontrado em nenhum banco.")
        return None


# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    db = conectar_mongodb()
    r = conectar_redis()

    if db is not None and r is not None:
        print("\n--- INICIANDO OPERAÇÕES MONGODB ---")
        popular_mongodb(db)
        print("Produtos com preço > 10:", consultar_preco_maior_10(db))
        atualizar_preco(db, "Mouse", 120.00)
        remover_por_categoria(db, "Papelaria")
        
        print("\n--- INICIANDO OPERAÇÕES REDIS ---")
        operacoes_basicas_redis(r)
        
        print("\n--- INICIANDO CASO INTEGRADO (CACHE) ---")
        # Primeira busca: Vai bater no MongoDB e salvar no Redis
        print(">> Primeira Busca:")
        dados1 = buscar_produto_com_cache(db, r, "Notebook")
        print("Resultado 1:", dados1)
        
        # Segunda busca: Vai encontrar direto no Redis
        print("\n>> Segunda Busca (Logo em seguida):")
        dados2 = buscar_produto_com_cache(db, r, "Notebook")
        print("Resultado 2:", dados2)
        
        print("\n🎉 Atividade concluída com sucesso!")