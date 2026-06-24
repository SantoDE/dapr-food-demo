{
  description = "Dapr Food Demo dev shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            # Kubernetes
            kubectl
            k3d
            devspace

            # Build
            docker

            # Dapr
            dapr-cli

            # Python
            python312
            python312Packages.pip
            python312Packages.virtualenv

            # Utils
            jq
            curl
          ];

          env = {
            DOCKER_API_VERSION = "1.41";
          };

          shellHook = ''
            echo "🍔🍺 Dapr Food Demo — dev shell"
            echo "  kubectl  $(kubectl version --client -o json 2>/dev/null | jq -r '.clientVersion.gitVersion')"
            echo "  k3d      $(k3d version | head -1)"
            echo "  devspace $(devspace version)"
            echo "  pack     $(pack version)"
            echo "  dapr     $(dapr version --client-only 2>/dev/null)"
            echo ""
          '';
        };
      });
}
