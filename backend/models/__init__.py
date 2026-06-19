from sqlalchemy import (
    Column, Integer, String, Float, Date, Boolean, ForeignKey, Text, create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker, Session


class Base(DeclarativeBase):
    pass


class Persona(Base):
    __tablename__ = "persona"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codice_fiscale = Column(String(16), unique=True, nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    cognome = Column(String(100), nullable=False)
    data_nascita = Column(Date, nullable=True)
    sesso = Column(String(1), nullable=True)
    comune_nascita = Column(String(100), nullable=True)
    provincia_nascita = Column(String(2), nullable=True)

    dichiarazioni = relationship("Dichiarazione", back_populates="persona", cascade="all, delete-orphan")


class Dichiarazione(Base):
    __tablename__ = "dichiarazione"

    id = Column(Integer, primary_key=True, autoincrement=True)
    persona_id = Column(Integer, ForeignKey("persona.id"), nullable=False, index=True)
    anno_fiscale = Column(Integer, nullable=False)
    tipo = Column(String(20), nullable=False, default="730")
    congiunta = Column(Boolean, default=False)
    note = Column(Text, nullable=True)

    persona = relationship("Persona", back_populates="dichiarazioni")
    quadri_a = relationship("QuadroA_Terreni", back_populates="dichiarazione", cascade="all, delete-orphan")
    quadri_b = relationship("QuadroB_Fabbricati", back_populates="dichiarazione", cascade="all, delete-orphan")
    quadri_c = relationship("QuadroC_Lavoro", back_populates="dichiarazione", cascade="all, delete-orphan")
    quadri_d = relationship("QuadroD_AltriRedditi", back_populates="dichiarazione", cascade="all, delete-orphan")
    quadri_e = relationship("QuadroE_Oneri", back_populates="dichiarazione", cascade="all, delete-orphan")
    risultato = relationship("Risultato", back_populates="dichiarazione", uselist=False, cascade="all, delete-orphan")


class QuadroA_Terreni(Base):
    __tablename__ = "quadro_a_terreni"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dichiarazione_id = Column(Integer, ForeignKey("dichiarazione.id"), nullable=False, index=True)
    rigo = Column(Integer, nullable=False)
    reddito_dominicale = Column(Float, default=0)
    reddito_agrario = Column(Float, default=0)
    titolo = Column(String(50), nullable=True)
    possesso = Column(String(50), nullable=True)
    giorni = Column(Integer, nullable=True)
    percentuale = Column(Float, default=100)
    canone_affitto = Column(Float, default=0)
    continuazione_rigo = Column(Integer, nullable=True)

    dichiarazione = relationship("Dichiarazione", back_populates="quadri_a")


class QuadroB_Fabbricati(Base):
    __tablename__ = "quadro_b_fabbricati"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dichiarazione_id = Column(Integer, ForeignKey("dichiarazione.id"), nullable=False, index=True)
    rigo = Column(Integer, nullable=False)
    rendita = Column(Float, default=0)
    canone_locazione = Column(Float, default=0)
    codice_catastale = Column(String(50), nullable=True)
    giorni_possesso = Column(Integer, nullable=True)
    percentuale = Column(Float, default=100)
    utilizzo = Column(String(50), nullable=True)

    dichiarazione = relationship("Dichiarazione", back_populates="quadri_b")


class QuadroC_Lavoro(Base):
    __tablename__ = "quadro_c_lavoro"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dichiarazione_id = Column(Integer, ForeignKey("dichiarazione.id"), nullable=False, index=True)
    rigo = Column(Integer, nullable=False)
    reddito = Column(Float, default=0)
    giorni = Column(Integer, nullable=True)
    ritenute = Column(Float, default=0)
    codice_cu = Column(String(20), nullable=True)
    tipologia = Column(String(50), default="dipendente")

    dichiarazione = relationship("Dichiarazione", back_populates="quadri_c")


class QuadroD_AltriRedditi(Base):
    __tablename__ = "quadro_d_altri_redditi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dichiarazione_id = Column(Integer, ForeignKey("dichiarazione.id"), nullable=False, index=True)
    rigo = Column(Integer, nullable=False)
    tipologia = Column(String(100), nullable=True)
    importo = Column(Float, default=0)
    ritenute = Column(Float, default=0)
    note = Column(Text, nullable=True)

    dichiarazione = relationship("Dichiarazione", back_populates="quadri_d")


class QuadroE_Oneri(Base):
    __tablename__ = "quadro_e_oneri"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dichiarazione_id = Column(Integer, ForeignKey("dichiarazione.id"), nullable=False, index=True)
    codice_rigo = Column(String(5), nullable=False)
    descrizione = Column(String(200), nullable=True)
    importo = Column(Float, default=0)
    rateizzata = Column(Boolean, default=False)
    numero_rate = Column(Integer, nullable=True)
    importo_rata_corrente = Column(Float, default=0)

    dichiarazione = relationship("Dichiarazione", back_populates="quadri_e")


class Risultato(Base):
    __tablename__ = "risultato"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dichiarazione_id = Column(Integer, ForeignKey("dichiarazione.id"), nullable=False, unique=True, index=True)
    imposta_netta = Column(Float, default=0)
    ritenute = Column(Float, default=0)
    differenza = Column(Float, default=0)
    esito = Column(String(10), default="pareggio")

    addiz_regionale_dovuta = Column(Float, default=0)
    addiz_regionale_certificazione = Column(Float, default=0)
    addiz_comunale_dovuta = Column(Float, default=0)
    addiz_comunale_certificazione = Column(Float, default=0)

    acconto_irpef_prima_rata = Column(Float, default=0)
    acconto_irpef_seconda_rata = Column(Float, default=0)
    acconto_cedolare_prima_rata = Column(Float, default=0)
    acconto_cedolare_seconda_rata = Column(Float, default=0)

    reddito_complessivo = Column(Float, default=0)
    reddito_imponibile = Column(Float, default=0)
    imposta_lorda = Column(Float, default=0)
    detrazione_lavoro_dipendente = Column(Float, default=0)
    detrazione_oneri = Column(Float, default=0)
    detrazione_recupero_edilizio = Column(Float, default=0)
    detrazione_risparmio_energetico = Column(Float, default=0)
    eccedenza_precedente = Column(Float, default=0)
    acconti_versati = Column(Float, default=0)

    dichiarazione = relationship("Dichiarazione", back_populates="risultato")


def create_engine_session(db_path: str = "backend/analyzer.db") -> tuple:
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal
