
    zookeeper-service:
        image: zookeeper:3.5.6
        environment:
            ZOO_MAX_CLIENT_CNXNS: '160000'
            ZOO_AUTOPURGE_PURGEINTERVAL: '1'
            ZOO_LOG4J_PROP: 'ERROR'
        networks:
            - appnet
        deploy:
            replicas: 1
            placement:
                constraints:
                    - node.role==manager

