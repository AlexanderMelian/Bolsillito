-- Se ejecuta automáticamente por la imagen oficial de Postgres solo la PRIMERA vez que se
-- crea el volumen de datos (docker-entrypoint-initdb.d). Crea una base separada para la suite
-- de tests de integración (backend/tests/conftest.py), para no pisar datos de desarrollo.
CREATE DATABASE bolsillito_test;
