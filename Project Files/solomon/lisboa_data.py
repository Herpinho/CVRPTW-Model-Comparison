DEPOSITO = {
    "id":           0,
    "nome":         "Armazém Central (Marquês de Pombal)",
    "lat":          38.7252,
    "lon":          -9.1500,
    "demand":       0,
    "ready_time":   0,      # 07:00
    "due_time":     720,    # 19:00
    "service_time": 0,
}

# Clientes — 20 pontos reais 


CLIENTES = [
    
    {
        "id": 1, "nome": "Hotel Tivoli Avenida",
        "lat": 38.7219, "lon": -9.1461,
        "demand": 30, "ready_time": 60, "due_time": 180, "service_time": 15,
        "tipo": "Hotel"
    },
    {
        "id": 2, "nome": "Hotel Sheraton Lisboa",
        "lat": 38.7267, "lon": -9.1547,
        "demand": 40, "ready_time": 60, "due_time": 180, "service_time": 15,
        "tipo": "Hotel"
    },
    {
        "id": 3, "nome": "Hotel Intercontinental",
        "lat": 38.7199, "lon": -9.1438,
        "demand": 35, "ready_time": 60, "due_time": 180, "service_time": 15,
        "tipo": "Hotel"
    },
    {
        "id": 4, "nome": "Hotel Altis Avenida",
        "lat": 38.7172, "lon": -9.1403,
        "demand": 25, "ready_time": 60, "due_time": 240, "service_time": 15,
        "tipo": "Hotel"
    },

    {
        "id": 5, "nome": "Pingo Doce Avenida da Liberdade",
        "lat": 38.7190, "lon": -9.1444,
        "demand": 80, "ready_time": 60, "due_time": 360, "service_time": 20,
        "tipo": "Supermercado"
    },
    {
        "id": 6, "nome": "Continente Bom Dia Marquês",
        "lat": 38.7260, "lon": -9.1512,
        "demand": 90, "ready_time": 60, "due_time": 360, "service_time": 20,
        "tipo": "Supermercado"
    },
    {
        "id": 7, "nome": "Lidl Rua Braamcamp",
        "lat": 38.7241, "lon": -9.1482,
        "demand": 70, "ready_time": 120, "due_time": 420, "service_time": 20,
        "tipo": "Supermercado"
    },

    {
        "id": 8, "nome": "Restaurante Solar dos Presuntos",
        "lat": 38.7162, "lon": -9.1388,
        "demand": 20, "ready_time": 120, "due_time": 240, "service_time": 10,
        "tipo": "Restaurante"
    },
    {
        "id": 9, "nome": "Restaurante Eleven",
        "lat": 38.7295, "lon": -9.1558,
        "demand": 15, "ready_time": 120, "due_time": 240, "service_time": 10,
        "tipo": "Restaurante"
    },
    {
        "id": 10, "nome": "Restaurante Bairro do Avillez",
        "lat": 38.7180, "lon": -9.1420,
        "demand": 25, "ready_time": 120, "due_time": 240, "service_time": 10,
        "tipo": "Restaurante"
    },
    {
        "id": 11, "nome": "Café A Brasileira",
        "lat": 38.7143, "lon": -9.1426,
        "demand": 10, "ready_time": 60, "due_time": 180, "service_time": 10,
        "tipo": "Restaurante"
    },

    {
        "id": 12, "nome": "Farmácia Marquês de Pombal",
        "lat": 38.7253, "lon": -9.1495,
        "demand": 15, "ready_time": 120, "due_time": 480, "service_time": 10,
        "tipo": "Farmácia"
    },
    {
        "id": 13, "nome": "Farmácia Avenida da Liberdade",
        "lat": 38.7208, "lon": -9.1452,
        "demand": 10, "ready_time": 120, "due_time": 480, "service_time": 10,
        "tipo": "Farmácia"
    },
    {
        "id": 14, "nome": "Farmácia Rua Rodrigues Sampaio",
        "lat": 38.7231, "lon": -9.1467,
        "demand": 12, "ready_time": 120, "due_time": 480, "service_time": 10,
        "tipo": "Farmácia"
    },

    {
        "id": 15, "nome": "Edifício Avenida Fontes Pereira de Melo",
        "lat": 38.7275, "lon": -9.1520,
        "demand": 50, "ready_time": 120, "due_time": 300, "service_time": 15,
        "tipo": "Escritório"
    },
    {
        "id": 16, "nome": "Torre Picoas Plaza",
        "lat": 38.7285, "lon": -9.1505,
        "demand": 45, "ready_time": 120, "due_time": 300, "service_time": 15,
        "tipo": "Escritório"
    },
    {
        "id": 17, "nome": "Edifício Atrium Saldanha",
        "lat": 38.7312, "lon": -9.1445,
        "demand": 55, "ready_time": 120, "due_time": 360, "service_time": 15,
        "tipo": "Escritório"
    },
    {
        "id": 18, "nome": "Escritórios Rua Castilho",
        "lat": 38.7238, "lon": -9.1520,
        "demand": 35, "ready_time": 180, "due_time": 360, "service_time": 15,
        "tipo": "Escritório"
    },

    {
        "id": 19, "nome": "El Corte Inglés Lisboa",
        "lat": 38.7262, "lon": -9.1538,
        "demand": 60, "ready_time": 120, "due_time": 420, "service_time": 20,
        "tipo": "Comércio"
    },
    {
        "id": 20, "nome": "Clínica CUF Marquês",
        "lat": 38.7248, "lon": -9.1488,
        "demand": 20, "ready_time": 60,  "due_time": 300, "service_time": 10,
        "tipo": "Clínica"
    },
]

NUM_VEHICLES    = 5
VEHICLE_CAPACITY = 200