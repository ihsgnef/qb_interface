## PostgreSQL server
1. Create DB cluster `initdb -D /fs/clip-quiz/shifeng/postgres`
2. Create the runtime directory `/fs/clip-quiz/shifeng/postgres/run`
3. Open `/fs/clip-quiz/shifeng/postgres/postgresql.conf`, find `unix_socket_directories` and point it to the runtime directory created above. 
4. Start the server `postgres -D /fs/clip-quiz/shifeng/postgres -p 5433`
5. Create DB `createdb -h /fs/clip-quiz/shifeng/postgres/run -p 5433 karl-prod`
6. Creat dump `pg_dump karl-prod -h /fs/clip-quiz/shifeng/postgres/run -p 5433 | gzip > /fs/clip-quiz/shifeng/karl/backup/karl-prod_20201017.gz`
