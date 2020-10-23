with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "coronaampel-dresden";
  buildInputs = with pkgs; [
    python3Packages.selenium
  ];
}
