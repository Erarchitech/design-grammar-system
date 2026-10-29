# F-01 (2026-10-29): dg-evaluator, the DG.Core rule evaluator as an internal HTTP service.
# Build context: ./DG (the evaluator project references ../../src/DG.Core).
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY src/DG.Core/ src/DG.Core/
COPY tools/DG.Evaluator/ tools/DG.Evaluator/
RUN dotnet publish tools/DG.Evaluator/DG.Evaluator.csproj -c Release -f net9.0 -o /out

FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /app
COPY --from=build /out .
ENV ASPNETCORE_URLS=http://0.0.0.0:8080
EXPOSE 8080
USER app
ENTRYPOINT ["dotnet", "DG.Evaluator.dll"]
