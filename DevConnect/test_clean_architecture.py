from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional
import unittest

# ==========================================
# 1. EXCEPCIONES Y ENTITIES (Domain Layer)
# ==========================================
class DomainException(Exception):
    """Excepción específica para violaciones a las reglas de negocio."""
    pass

@dataclass
class Vacancy:
    id: str
    project_id: str
    available_slots: int
    is_closed: bool = False

    def decrementar_cupo(self):
        """Regla de Negocio: No permitir sobrecupos y cerrar al llegar a 0."""
        if self.available_slots <= 0 or self.is_closed:
            raise DomainException("No hay cupos disponibles. La vacante está llena o cerrada.")
        
        self.available_slots -= 1
        
        if self.available_slots == 0:
            self.is_closed = True

@dataclass
class Application:
    id: str
    vacancy_id: str
    student_id: str
    status: str = "PENDIENTE"

    def aceptar(self):
        if self.status != "PENDIENTE":
            raise DomainException("Solo se pueden aceptar postulaciones pendientes.")
        self.status = "ACEPTADA"

# ==========================================
# 2. REPOSITORY INTERFACES (Domain/App Layer)
# ==========================================
class IVacancyRepository(ABC):
    @abstractmethod
    def find_by_id(self, vacancy_id: str) -> Optional[Vacancy]: pass
    
    @abstractmethod
    def save(self, vacancy: Vacancy) -> Vacancy: pass

class IApplicationRepository(ABC):
    @abstractmethod
    def find_by_id(self, application_id: str) -> Optional[Application]: pass
    
    @abstractmethod
    def save(self, application: Application) -> Application: pass

# ==========================================
# 3. ADAPTERS EN MEMORIA (Infrastructure Layer)
# ==========================================
class InMemoryVacancyRepository(IVacancyRepository):
    def __init__(self):
        self.db = {} # Simulamos una base de datos con un diccionario

    def find_by_id(self, vacancy_id: str) -> Optional[Vacancy]:
        return self.db.get(vacancy_id)

    def save(self, vacancy: Vacancy) -> Vacancy:
        self.db[vacancy.id] = vacancy
        return vacancy

class InMemoryApplicationRepository(IApplicationRepository):
    def __init__(self):
        self.db = {}

    def find_by_id(self, application_id: str) -> Optional[Application]:
        return self.db.get(application_id)

    def save(self, application: Application) -> Application:
        self.db[application.id] = application
        return application

# ==========================================
# 4. USE CASE (Application Layer)
# ==========================================
class AcceptApplicationUseCase:
    def __init__(self, vacancy_repo: IVacancyRepository, app_repo: IApplicationRepository):
        # Inyección de dependencias (solo conocemos interfaces, no implementaciones)
        self.vacancy_repo = vacancy_repo
        self.app_repo = app_repo

    def execute(self, application_id: str) -> Application:
        # 1. Recuperar datos
        app = self.app_repo.find_by_id(application_id)
        if not app:
            raise ValueError("La postulación no existe.")

        vacancy = self.vacancy_repo.find_by_id(app.vacancy_id)
        if not vacancy:
            raise ValueError("La vacante no existe.")

        # 2. Ejecutar lógica y reglas de negocio puras (Entities)
        vacancy.decrementar_cupo()
        app.aceptar()

        # 3. Persistir cambios
        self.vacancy_repo.save(vacancy)
        self.app_repo.save(app)

        return app

#Pruebas unitarias (Testing)
import unittest

class TestAcceptApplicationUseCase(unittest.TestCase):
    def setUp(self):
        # Preparamos el entorno inyectando los adaptadores en memoria
        self.vacancy_repo = InMemoryVacancyRepository()
        self.app_repo = InMemoryApplicationRepository()
        self.use_case = AcceptApplicationUseCase(self.vacancy_repo, self.app_repo)

    def test_aceptar_postulacion_con_exito(self):
        """Prueba 1: Flujo feliz. Hay cupo y se asigna correctamente."""
        # Arrange (Preparar datos)
        vacancy = Vacancy(id="vac-1", project_id="proj-1", available_slots=1)
        app = Application(id="app-1", vacancy_id="vac-1", student_id="stu-99")
        
        self.vacancy_repo.save(vacancy)
        self.app_repo.save(app)

        # Act (Ejecutar caso de uso)
        result = self.use_case.execute("app-1")

        # Assert (Verificar resultados)
        self.assertEqual(result.status, "ACEPTADA")
        
        updated_vacancy = self.vacancy_repo.find_by_id("vac-1")
        self.assertEqual(updated_vacancy.available_slots, 0)
        self.assertTrue(updated_vacancy.is_closed, "La vacante debió cerrarse al llegar a 0.")

    def test_falla_al_aceptar_sin_cupos(self):
        """Prueba 2: Regla de negocio. Falla si intentamos aceptar a alguien en una vacante llena."""
        # Arrange (Preparar datos simulando una vacante ya ocupada)
        vacancy = Vacancy(id="vac-2", project_id="proj-1", available_slots=0, is_closed=True)
        app = Application(id="app-2", vacancy_id="vac-2", student_id="stu-88")
        
        self.vacancy_repo.save(vacancy)
        self.app_repo.save(app)

        # Act & Assert (Verificamos que nuestra Entity lance el DomainException)
        with self.assertRaises(DomainException) as context:
            self.use_case.execute("app-2")

        self.assertIn("No hay cupos disponibles", str(context.exception))

if __name__ == '__main__':
    unittest.main()

#PARTE 4: ADAPTERS JSON (Infrastructure Layer)
import json
import os
from typing import Optional
# (Asumimos que Vacancy, Application, IVacancyRepository e IApplicationRepository ya están importados de la Parte 3)

class JsonVacancyRepository(IVacancyRepository):
    def __init__(self, file_path: str = "vacancies.json"):
        self.file_path = file_path
        # Crea el archivo vacío si no existe
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)

    def _read_file(self) -> dict:
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def _write_file(self, data: dict):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def find_by_id(self, vacancy_id: str) -> Optional[Vacancy]:
        data = self._read_file()
        if vacancy_id in data:
            v_data = data[vacancy_id]
            # Reconstruimos la Entity desde el diccionario JSON
            return Vacancy(
                id=v_data['id'],
                project_id=v_data['project_id'],
                available_slots=v_data['available_slots'],
                is_closed=v_data['is_closed']
            )
        return None

    def save(self, vacancy: Vacancy) -> Vacancy:
        data = self._read_file()
        # Serializamos la Entity a un diccionario JSON
        data[vacancy.id] = {
            "id": vacancy.id,
            "project_id": vacancy.project_id,
            "available_slots": vacancy.available_slots,
            "is_closed": vacancy.is_closed
        }
        self._write_file(data)
        return vacancy

class JsonApplicationRepository(IApplicationRepository):
    def __init__(self, file_path: str = "applications.json"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)

    def _read_file(self) -> dict:
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def _write_file(self, data: dict):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def find_by_id(self, application_id: str) -> Optional[Application]:
        data = self._read_file()
        if application_id in data:
            a_data = data[application_id]
            return Application(
                id=a_data['id'],
                vacancy_id=a_data['vacancy_id'],
                student_id=a_data['student_id'],
                status=a_data['status']
            )
        return None

    def save(self, application: Application) -> Application:
        data = self._read_file()
        data[application.id] = {
            "id": application.id,
            "vacancy_id": application.vacancy_id,
            "student_id": application.student_id,
            "status": application.status
        }
        self._write_file(data)
        return application

    # ANTES (Parte 3):
# vacancy_repo = InMemoryVacancyRepository()
# app_repo = InMemoryApplicationRepository()

# AHORA (Parte 4 - Swap completado):
vacancy_repo = JsonVacancyRepository("datos_vacantes.json")
app_repo = JsonApplicationRepository("datos_postulaciones.json")

# EL CASO DE USO SIGUE INTACTO:
use_case = AcceptApplicationUseCase(vacancy_repo, app_repo)
resultado = use_case.execute("app-1")