# Client patch

Adventurer Core owns the generated WotLK 3.3.5a `Z` patch family used to expose class ID 10 and its native talent trees to the client.

The build/install pipeline is transactional and must keep the server and client DBC payload byte-identical.
