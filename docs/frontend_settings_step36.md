# Tela Configurações

O frontend envia somente os campos aceitos pelo schema de atualização.

`updated_at_utc` pertence ao servidor e não é incluído no PATCH.

Campos científicos extras são rejeitados pelo backend com HTTP 422.
