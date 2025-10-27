from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    max_number_of_sentences_in_one_chunk: int
    questions_per_chunk: int
    default_admin_email: str
    default_admin_password: str
    clarin_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
