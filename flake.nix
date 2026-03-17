{
  description = "A Nix-flake-based Python development environment";

  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1"; # unstable Nixpkgs

  outputs =
    { self, ... }@inputs:

    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSupportedSystem =
        f:
        inputs.nixpkgs.lib.genAttrs supportedSystems (
          system:
          f {
            pkgs = import inputs.nixpkgs { inherit system; };
          }
        );

      /*
        Change this value ({major}.{min}) to
        update the Python virtual-environment
        version. When you do this, make sure
        to delete the `.venv` directory to
        have the hook rebuild it for the new
        version, since it won't overwrite an
        existing one. After this, reload the
        development shell to rebuild it.
        You'll see a warning asking you to
        do this when version mismatches are
        present. For safety, removal should
        be a manual step, even if trivial.
      */
      version = "3.13";
    in
    {
      devShells = forEachSupportedSystem (
        { pkgs }:
        let
          concatMajorMinor =
            v:
            pkgs.lib.pipe v [
              pkgs.lib.versions.splitVersion
              (pkgs.lib.sublist 0 2)
              pkgs.lib.concatStrings
            ];

          python = pkgs."python${concatMajorMinor version}";
        in
        {
          default = pkgs.mkShellNoCC {
            venvDir = ".venv";

            postShellHook = ''
              venvVersionWarn() {
              	local venvVersion
              	venvVersion="$("$venvDir/bin/python" -c 'import platform; print(platform.python_version())')"

              	[[ "$venvVersion" == "${python.version}" ]] && return

              	cat <<EOF
              Warning: Python version mismatch: [$venvVersion (venv)] != [${python.version}]
                       Delete '$venvDir' and reload to rebuild for version ${python.version}
              EOF
              }

              venvVersionWarn
            '';

            packages = with python.pkgs; [
              venvShellHook
              pip
              python-lsp-server

              pytest # Framework for writing tests
              requests # HTTP library for Python
              fastapi # Web framework for building APIs
              uvicorn # Lightning-fast ASGI server
              pytest-mock # Thin wrapper around the mock package for easier use with pytest
              pymysql # Pure Python MySQL client
              alembic # Database migration tool for SQLAlchemy
              cryptography # Package which provides cryptographic recipes and primitives

              httpx # Next generation HTTP client
              python-http-client # Python HTTP library to call APIs
              sqlmodel # Module to work with SQL databases

              sqlalchemy # Python SQL toolkit and Object Relationa Mapper
              python-dotenv # Add .env support to your django/flask apps in development and deployments
              python-jose # JOSE implementation in Pyhthon
              pydantic # Data validation and settings management using Python type hinting
              pydantic-settings # Settings management using pydantic
              email-validator # Perform basic syntax and deliverablity checks on email addresses
              bcrypt # Modern password hasing for your software and your servers
              python-multipart # Streaming multipart parser for Python
              jwt # Super fast CLI tool to decode and encode JWTs
              pyjwt # JSON Web Token implementation in Python
              redis # Python client for Redis key-value store

              # Add whatever else you'd like here.
              pkgs.basedpyright
              # pkgs.black
              # or
              python.pkgs.black
              pkgs.ruff
              # or
              # python.pkgs.ruff

            ];
          };
        }
      );
    };
}
