from mof_bandgap.config import Settings


def main() -> None:
    settings = Settings()
    print(f"hello world, app_env={settings.app_env}")


if __name__ == "__main__":
    main()
