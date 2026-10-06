#ifndef ALADYN_ENGINE_PEN_POSE_HPP
#define ALADYN_ENGINE_PEN_POSE_HPP

namespace aladyn::engine::stroke {

// A posição da caneta na última amostra do traço (altitude 90° = em pé; mouse). Os carimbos que o motor cria sem
// uma amostra nova (o de alcance do estabilizador na soltura, o do afunilamento) herdam a inclinação em vez de
// sair com a caneta em pé.
struct PenPose {
    double altitude{90.0};
    double azimuth{0.0};
    double twist{0.0};
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_PEN_POSE_HPP
